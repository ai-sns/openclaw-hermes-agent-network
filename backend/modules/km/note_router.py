# -*- coding: utf-8 -*-
"""
KM Note Router - Note API router
"""
import logging
from fastapi import APIRouter, HTTPException
from typing import List

import re
from html import unescape
from sqlalchemy import and_

from backend.database.base import SessionLocal
from backend.database.models.km import NoteMng
from .vector_service import get_vector_service

from .note_schemas import NoteCreate, NoteUpdate, NoteResponse
from .note_service import NoteService

logger = logging.getLogger(__name__)

router = APIRouter()
note_service = NoteService()


def _html_to_text(html: str) -> str:
    if not html:
        return ''
    try:
        cleaned = re.sub(r'<(script|style)[^>]*>[\s\S]*?</\\1>', ' ', html, flags=re.IGNORECASE)
        cleaned = re.sub(r'<[^>]+>', ' ', cleaned)
        cleaned = unescape(cleaned)
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        return cleaned
    except Exception:
        return str(html)


@router.get("/notes", response_model=List[NoteResponse])
async def get_all_notes():
    """Get the list of all notes."""
    try:
        notes = note_service.get_all_notes()
        return notes
    except Exception as e:
        logger.error(f"Error getting notes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/notes/search", response_model=List[NoteResponse])
async def search_notes(query: str = "", km_id: str = None):
    """Search notes (supports title, content, and tag search)."""
    try:
        notes = note_service.search_notes(query=query, km_id=km_id)
        return notes
    except Exception as e:
        logger.error(f"Error searching notes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/notes/{note_id}", response_model=NoteResponse)
async def get_note(note_id: int):
    """Get a single note."""
    try:
        note = note_service.get_note(note_id)
        if not note:
            raise HTTPException(status_code=404, detail="Note not found")
        return note
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting note: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/notes", response_model=NoteResponse)
async def create_note(note_data: NoteCreate):
    """Create a new note."""
    try:
        note = note_service.create_note(
            title=note_data.title,
            content=note_data.content,
            tags=note_data.tags,
            km_id=note_data.km_id  # Pass km_id to service
        )
        return note
    except Exception as e:
        logger.error(f"Error creating note: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/notes/{note_id}", response_model=NoteResponse)
async def update_note(note_id: int, note_data: NoteUpdate):
    """Update a note."""
    try:
        note = note_service.update_note(
            note_id=note_id,
            title=note_data.title,
            content=note_data.content,
            tags=note_data.tags,
            is_pinned=note_data.is_pinned
        )
        if not note:
            raise HTTPException(status_code=404, detail="Note not found")
        return note
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating note: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/notes/{note_id}")
async def delete_note(note_id: int):
    """Delete a note."""
    try:
        km_id_str = None
        session = SessionLocal()
        try:
            note = session.query(NoteMng).filter(
                and_(NoteMng.id == note_id, NoteMng.is_delete == False)
            ).first()
            km_id_str = getattr(note, 'km_id', None) if note else None
        finally:
            session.close()

        success = note_service.delete_note(note_id)
        if not success:
            raise HTTPException(status_code=404, detail="Note not found")

        if km_id_str:
            try:
                vector_service = get_vector_service()
                vector_service.delete_note(km_id_str, note_id)
            except Exception as e:
                logger.warning(f"Failed to delete note vectors for note_id={note_id}: {e}")
        return {"success": True, "message": "Note deleted"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting note: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/notes/{note_id}/vectorize", response_model=dict)
async def vectorize_note(note_id: int, request: dict):
    try:
        chunk_size = int(request.get('chunk_size') or 1000)
        overlap = int(request.get('overlap') or 100)
        km_id_req = request.get('km_id')

        session = SessionLocal()
        try:
            note = session.query(NoteMng).filter(
                and_(NoteMng.id == note_id, NoteMng.is_delete == False)
            ).first()
            if not note:
                raise HTTPException(status_code=404, detail="Note not found")

            km_id_str = getattr(note, 'km_id', None) or km_id_req
            if not km_id_str:
                raise HTTPException(status_code=400, detail="km_id is required")

            try:
                from db.write_queue import db_write
                _nid = note_id
                def _do_set_wait(sess):
                    from backend.database.models.km import NoteMng as _NM
                    rec = sess.query(_NM).filter(_NM.id == _nid).first()
                    if rec:
                        rec.waitvectorization = True
                db_write(_do_set_wait, description="note_router_set_wait_vectorization")
            except Exception:
                pass

            title = getattr(note, 'title', '') or ''
            content = getattr(note, 'content', '') or ''
            text = _html_to_text(content)

            vector_service = get_vector_service()
            chunks = vector_service.upsert_note(
                km_id=km_id_str,
                note_id=note_id,
                title=title,
                text=text,
                chunk_size=chunk_size,
                overlap=overlap
            )

            try:
                from db.write_queue import db_write
                _nid2 = note_id
                def _do_clear_wait(sess):
                    from backend.database.models.km import NoteMng as _NM
                    rec = sess.query(_NM).filter(_NM.id == _nid2).first()
                    if rec:
                        rec.waitvectorization = False
                db_write(_do_clear_wait, description="note_router_clear_wait_vectorization")
            except Exception:
                pass

            return {"success": True, "data": {"note_id": note_id, "chunks": int(chunks or 0)}}
        finally:
            session.close()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error vectorizing note: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/notes/vector-search", response_model=dict)
async def vector_search_notes(request: dict):
    try:
        km_id_str = request.get('km_id')
        query = request.get('query') or ''
        top_k = int(request.get('top_k') or 5)

        if not km_id_str:
            raise HTTPException(status_code=400, detail="km_id is required")
        if not query.strip():
            raise HTTPException(status_code=400, detail="query is required")

        vector_service = get_vector_service()
        results = vector_service.search(km_id_str, query, top_k)
        return {"success": True, "data": results}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error performing note vector search: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/notes/{note_id}/toggle-pin", response_model=NoteResponse)
async def toggle_pin_note(note_id: int):
    """Toggle note pinned status."""
    try:
        note = note_service.toggle_pin(note_id)
        if not note:
            raise HTTPException(status_code=404, detail="Note not found")
        return note
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error toggling pin: {e}")
        raise HTTPException(status_code=500, detail=str(e))
