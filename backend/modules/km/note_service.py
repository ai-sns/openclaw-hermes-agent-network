# -*- coding: utf-8 -*-
"""
KM Note Service - Note service (backward compatible version)
Uses SQLite database to store note data, compatible with legacy table structure
"""
import json
from datetime import datetime
from typing import List, Optional, Dict
from sqlalchemy import and_, or_, text
from sqlalchemy.orm import Session

from backend.database.base import SessionLocal, create_all_tables, engine
from backend.database.models.km import NoteMng


class NoteService:
    """Note service class - uses SQLite database (backward compatible)."""

    def __init__(self):
        """Initialize the note service."""
        # Ensure database tables are created
        create_all_tables()

        # Check table schema and add missing columns
        self._ensure_columns()

    def _ensure_columns(self):
        """Ensure all required columns exist."""
        try:
            with engine.connect() as conn:
                # Check whether columns exist
                result = conn.execute(text("PRAGMA table_info(note_mng)"))
                columns = [row[1] for row in result]

                # Add missing columns
                if 'tags' not in columns:
                    try:
                        conn.execute(text("ALTER TABLE note_mng ADD COLUMN tags TEXT"))
                        conn.commit()
                        print("✅ Added tags column")
                    except Exception as e:
                        print(f"⚠️  Failed to add tags column: {e}")

                if 'is_pinned' not in columns:
                    try:
                        conn.execute(text("ALTER TABLE note_mng ADD COLUMN is_pinned BOOLEAN DEFAULT 0"))
                        conn.commit()
                        print("✅ Added is_pinned column")
                    except Exception as e:
                        print(f"⚠️  Failed to add is_pinned column: {e}")

                if 'updated_at' not in columns:
                    try:
                        conn.execute(text("ALTER TABLE note_mng ADD COLUMN updated_at DATETIME"))
                        conn.execute(text("UPDATE note_mng SET updated_at = create_time WHERE updated_at IS NULL"))
                        conn.commit()
                        print("✅ Added updated_at column")
                    except Exception as e:
                        print(f"⚠️  Failed to add updated_at column: {e}")

        except Exception as e:
            print(f"⚠️  Error while checking/adding columns: {e}")

    def _get_session(self) -> Session:
        """Get a database session."""
        return SessionLocal()

    def _note_to_dict(self, note: NoteMng) -> Dict:
        """Convert a DB model instance into a dict."""
        # Parse tags field
        tags = []
        if hasattr(note, 'tags') and note.tags:
            try:
                tags = json.loads(note.tags)
            except:
                tags = []

        # Safely read fields
        is_pinned = getattr(note, 'is_pinned', False) or False
        updated_at = getattr(note, 'updated_at', None)

        if not updated_at and note.create_time:
            updated_at = note.create_time

        return {
            'id': note.id,
            'title': note.title or '',
            'content': note.content or '',
            'tags': tags,
            'is_pinned': is_pinned,
            'created_at': note.create_time.isoformat() if note.create_time else datetime.now().isoformat(),
            'updated_at': updated_at.isoformat() if updated_at else datetime.now().isoformat()
        }

    def create_note(self, title: str, content: str, tags: List[str] = None, km_id: str = None) -> Dict:
        """Create a new note."""
        session = self._get_session()
        try:
            now = datetime.now()
            note_data = {
                'title': title,
                'content': content,
                'is_delete': False,
                'create_time': now,
            }

            # Add km_id if provided
            if km_id:
                note_data['km_id'] = km_id

            # Only set extended fields if columns exist
            try:
                note_data['tags'] = json.dumps(tags or [], ensure_ascii=False)
                note_data['is_pinned'] = False
                note_data['updated_at'] = now
            except:
                pass

            note = NoteMng(**note_data)

            from db.write_queue import db_write
            _note_data = note_data
            def _do(sess):
                n = NoteMng(**_note_data)
                sess.add(n)
                sess.flush()
                sess.refresh(n)
                return n
            note = db_write(_do, description="note_service_create")

            return self._note_to_dict(note)
        except Exception as e:
            raise e
        finally:
            session.close()

    def get_all_notes(self) -> List[Dict]:
        """Get all notes (not deleted)."""
        session = self._get_session()
        try:
            notes = session.query(NoteMng).filter(
                NoteMng.is_delete == False
            ).all()

            return [self._note_to_dict(note) for note in notes]
        finally:
            session.close()

    def get_note(self, note_id: int) -> Optional[Dict]:
        """Get a single note."""
        session = self._get_session()
        try:
            note = session.query(NoteMng).filter(
                and_(
                    NoteMng.id == note_id,
                    NoteMng.is_delete == False
                )
            ).first()

            if note:
                return self._note_to_dict(note)
            return None
        finally:
            session.close()

    def update_note(self, note_id: int, title: str = None, content: str = None,
                   tags: List[str] = None, is_pinned: bool = None) -> Optional[Dict]:
        """Update a note."""
        session = self._get_session()
        try:
            note = session.query(NoteMng).filter(
                and_(
                    NoteMng.id == note_id,
                    NoteMng.is_delete == False
                )
            ).first()

            if not note:
                return None

            # Update fields
            if title is not None:
                note.title = title
            if content is not None:
                note.content = content

            # Only update extended fields if columns exist
            try:
                if tags is not None and hasattr(note, 'tags'):
                    note.tags = json.dumps(tags, ensure_ascii=False)
                if is_pinned is not None and hasattr(note, 'is_pinned'):
                    note.is_pinned = is_pinned
                    if is_pinned and hasattr(note, 'stick_time'):
                        note.stick_time = datetime.now()
                    elif hasattr(note, 'stick_time'):
                        note.stick_time = None
                if hasattr(note, 'updated_at'):
                    note.updated_at = datetime.now()
            except Exception as e:
                print(f"⚠️  Error while updating extended fields: {e}")

            from db.write_queue import db_write
            _nid = note_id
            _title = title
            _content = content
            _tags = tags
            _is_pinned = is_pinned
            def _do(sess):
                rec = sess.query(NoteMng).filter(and_(NoteMng.id == _nid, NoteMng.is_delete == False)).first()
                if not rec:
                    return None
                if _title is not None:
                    rec.title = _title
                if _content is not None:
                    rec.content = _content
                try:
                    if _tags is not None and hasattr(rec, 'tags'):
                        rec.tags = json.dumps(_tags, ensure_ascii=False)
                    if _is_pinned is not None and hasattr(rec, 'is_pinned'):
                        rec.is_pinned = _is_pinned
                        if _is_pinned and hasattr(rec, 'stick_time'):
                            rec.stick_time = datetime.now()
                        elif hasattr(rec, 'stick_time'):
                            rec.stick_time = None
                    if hasattr(rec, 'updated_at'):
                        rec.updated_at = datetime.now()
                except Exception:
                    pass
                sess.flush()
                sess.refresh(rec)
                return rec
            updated = db_write(_do, description="note_service_update")

            return self._note_to_dict(updated) if updated else None
        except Exception as e:
            raise e
        finally:
            session.close()

    def delete_note(self, note_id: int) -> bool:
        """Delete a note (soft delete)."""
        session = self._get_session()
        try:
            note = session.query(NoteMng).filter(
                and_(
                    NoteMng.id == note_id,
                    NoteMng.is_delete == False
                )
            ).first()

            if not note:
                return False

            from db.write_queue import db_write
            _nid = note_id
            def _do(sess):
                rec = sess.query(NoteMng).filter(and_(NoteMng.id == _nid, NoteMng.is_delete == False)).first()
                if not rec:
                    return False
                rec.is_delete = True
                try:
                    if hasattr(rec, 'updated_at'):
                        rec.updated_at = datetime.now()
                except:
                    pass
                return True
            return db_write(_do, description="note_service_delete")
        except Exception as e:
            raise e
        finally:
            session.close()

    def toggle_pin(self, note_id: int) -> Optional[Dict]:
        """Toggle note pinned status."""
        session = self._get_session()
        try:
            note = session.query(NoteMng).filter(
                and_(
                    NoteMng.id == note_id,
                    NoteMng.is_delete == False
                )
            ).first()

            if not note:
                return None

            from db.write_queue import db_write
            _nid = note_id
            def _do(sess):
                rec = sess.query(NoteMng).filter(and_(NoteMng.id == _nid, NoteMng.is_delete == False)).first()
                if not rec:
                    return None
                try:
                    if hasattr(rec, 'is_pinned'):
                        rec.is_pinned = not rec.is_pinned
                        if hasattr(rec, 'stick_time'):
                            rec.stick_time = datetime.now() if rec.is_pinned else None
                    if hasattr(rec, 'updated_at'):
                        rec.updated_at = datetime.now()
                except Exception:
                    pass
                sess.flush()
                sess.refresh(rec)
                return rec
            toggled = db_write(_do, description="note_service_toggle_pin")

            return self._note_to_dict(toggled) if toggled else None
        except Exception as e:
            raise e
        finally:
            session.close()


    def search_notes(self, query: str = "", km_id: str = None) -> List[Dict]:
        """
        Search notes.

        Args:
            query: Search keywords (search title/content/tags)
            km_id: Knowledge base ID (string, e.g. "note_store"; optional; used to filter notes in a specific KB)

        Returns:
            List of notes that match
        """
        session = SessionLocal()
        try:
            # Build query
            filters = [NoteMng.is_delete == False]

            # Add knowledge base filter
            if km_id is not None:
                filters.append(NoteMng.km_id == km_id)

            # Add search conditions
            if query and query.strip():
                search_term = f"%{query}%"
                filters.append(
                    or_(
                        NoteMng.title.like(search_term),
                        NoteMng.content.like(search_term),
                        NoteMng.tags.like(search_term)
                    )
                )

            # Execute query
            notes = session.query(NoteMng).filter(and_(*filters)).all()

            # Convert to list of dicts
            result = [self._note_to_dict(note) for note in notes]

            # Sort by pinned status and update time
            result.sort(key=lambda x: (
                not x.get('is_pinned', False),  # Pinned first
                -(datetime.fromisoformat(x.get('updated_at') or x.get('create_time') or datetime.now().isoformat()).timestamp())  # Newest first
            ))

            return result
        except Exception as e:
            raise e
        finally:
            session.close()
