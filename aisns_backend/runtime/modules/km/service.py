# -*- coding: utf-8 -*-
"""
KM module - Service layer
"""
import logging
from typing import List, Dict, Any
from pathlib import Path
import sqlite3

from db.DBFactory import (
    query_KMCfg_All,
    add_KMCfg,
    update_KMCfg,
    delete_KMCfg
)
from .vector_service import get_vector_service
from .document_loader import DocumentLoader

logger = logging.getLogger(__name__)


class KMService:
    """Service for managing knowledge bases"""

    @staticmethod
    def get_all_knowledge_bases() -> List[Dict[str, Any]]:
        """Get all knowledge bases"""
        kbs = query_KMCfg_All()
        result = []
        for kb in kbs:
            result.append({
                "id": kb.id,
                "km_id": getattr(kb, 'km_id', ''),
                "name": getattr(kb, 'name', ''),
                "memo": getattr(kb, 'memo', ''),
                "kmtype": getattr(kb, 'kmtype', '1'),
                "kmpath": getattr(kb, 'kmpath', ''),
                "is_show": getattr(kb, 'is_show', True),
                "is_delete": getattr(kb, 'is_delete', False)
            })
        return result

    @staticmethod
    def create_knowledge_base(**kwargs) -> int:
        km_id = kwargs.get('km_id')
        name = kwargs.get('name')
        memo = kwargs.get('memo', '')
        label = kwargs.get('label', '')
        kmpath = kwargs.get('kmpath', '')
        vectorization = kwargs.get('vectorization', True)
        stopvectorization = kwargs.get('stopvectorization', False)
        kmtype = kwargs.get('kmtype', 1)
        vectortype = kwargs.get('vectortype', '')
        embeddingmodel = kwargs.get('embeddingmodel', '')
        textblocklength = kwargs.get('textblocklength', 1000)
        overlaplength = kwargs.get('overlaplength', 100)
        titleaugment = kwargs.get('titleaugment', True)
        config_param = kwargs.get('config_param', '')

        kb_id = add_KMCfg(
            km_id=km_id,
            name=name,
            memo=memo,
            label=label,
            kmpath=kmpath,
            vectorization=vectorization,
            stopvectorization=stopvectorization,
            kmtype=kmtype,
            vectortype=vectortype,
            embeddingmodel=embeddingmodel,
            textblocklength=textblocklength,
            overlaplength=overlaplength,
            titleaugment=titleaugment,
            config_param=config_param,
        )
        return kb_id

    @staticmethod
    def update_knowledge_base(kb_id: int, **kwargs) -> None:
        """Update knowledge base configuration"""
        update_KMCfg(kb_id, **kwargs)

    @staticmethod
    def delete_knowledge_base(kb_id: int) -> None:
        """Delete a knowledge base"""
        delete_KMCfg(kb_id)

    @staticmethod
    def save_uploaded_file(kb_id: int, filename: str, content: bytes) -> Path:
        """
        Save uploaded file to knowledge base directory

        Args:
            kb_id: Knowledge base ID
            filename: File name
            content: File content

        Returns:
            Path to saved file
        """
        upload_dir = Path(f"km/uploads/{kb_id}")
        upload_dir.mkdir(parents=True, exist_ok=True)

        file_path = upload_dir / filename
        with open(file_path, "wb") as f:
            f.write(content)

        return file_path

    @staticmethod
    def get_files(kb_id: int) -> List[Dict[str, Any]]:
        """Get all files for a knowledge base"""
        conn = sqlite3.connect('db/db.sqlite')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            # Get km_id from km_cfg
            cursor.execute("SELECT km_id FROM km_cfg WHERE id = ?", (kb_id,))
            row = cursor.fetchone()
            if not row:
                return []

            km_id_str = row['km_id']

            # Get files from km_data
            cursor.execute("""
                SELECT id, km_id, filename, filenum, create_time
                FROM km_data
                WHERE km_id = ? AND (is_delete IS NULL OR is_delete = 0)
                ORDER BY create_time DESC
            """, (km_id_str,))

            files = []
            for row in cursor.fetchall():
                files.append({
                    "id": row['id'],
                    "km_id": row['km_id'],
                    "filename": row['filename'],
                    "filenum": row['filenum'],
                    "create_time": row['create_time']
                })

            return files
        finally:
            conn.close()

    @staticmethod
    def add_file(kb_id: int, filename: str, content: bytes) -> int:
        """Add a file to knowledge base and vectorize it"""
        conn = sqlite3.connect('db/db.sqlite')
        cursor = conn.cursor()

        try:
            file_ext = Path(filename).suffix.lower()
            allowed_exts = {
                '.doc', '.docx',
                '.txt',
                '.md', '.markdown',
                '.pdf',
                '.ppt', '.pptx',
                '.xls', '.xlsx',
            }
            if file_ext not in allowed_exts:
                raise ValueError(
                    f"Unsupported file type: {file_ext or '(no extension)'}. Supported: doc, txt, markdown, pdf, ppt, excel"
                )

            # Get km_id from km_cfg
            cursor.execute("SELECT km_id, textblocklength, overlaplength FROM km_cfg WHERE id = ?", (kb_id,))
            row = cursor.fetchone()
            if not row:
                raise ValueError(f"Knowledge base {kb_id} not found")

            km_id_str = row[0]
            chunk_size = row[1] or 1000
            overlap = row[2] or 100

            # Save file
            upload_dir = Path(f"km/{km_id_str}/doc")
            upload_dir.mkdir(parents=True, exist_ok=True)
            file_path = upload_dir / filename
            with open(file_path, "wb") as f:
                f.write(content)

            # Insert into km_data
            from db.write_queue import db_write
            from sqlalchemy import text as sa_text
            _km_id_str = km_id_str
            _filename = filename
            def _do_insert(session):
                session.execute(sa_text(
                    "INSERT INTO km_data (km_id, filename, filenum, waitvectorization, is_delete, create_time) "
                    "VALUES (:km_id, :filename, 1, 1, 0, datetime('now'))"
                ), {"km_id": _km_id_str, "filename": _filename})
                session.flush()
                row = session.execute(sa_text("SELECT last_insert_rowid()")).scalar()
                return row
            file_id = db_write(_do_insert, description="km_service_insert_file")

            text = DocumentLoader.load_document(file_path)
            if not text:
                def _do_delete(session):
                    session.execute(sa_text("DELETE FROM km_data WHERE id = :fid"), {"fid": file_id})
                db_write(_do_delete, description="km_service_delete_failed_file")
                try:
                    file_path.unlink(missing_ok=True)
                except Exception:
                    pass
                raise ValueError(
                    f"File parsing failed or this file content is not supported yet: {file_ext}. Supported: doc, txt, markdown, pdf, ppt, excel"
                )

            # Vectorize the document
            try:
                vector_service = get_vector_service()
                chunks_count = vector_service.add_document(
                    km_id=km_id_str,
                    file_id=file_id,
                    filename=filename,
                    text=text,
                    chunk_size=chunk_size,
                    overlap=overlap
                )

                _chunks = int(chunks_count or 0)
                _fid = file_id
                def _do_update_vec(session):
                    session.execute(sa_text(
                        "UPDATE km_data SET waitvectorization = 0, filenum = :chunks WHERE id = :fid"
                    ), {"chunks": _chunks, "fid": _fid})
                db_write(_do_update_vec, description="km_service_update_vectorization")
                logger.info(f"Vectorized file {filename} into {chunks_count} chunks")
            except Exception as e:
                logger.error(f"Error vectorizing file {filename}: {e}")
                # Leave waitvectorization=1 to indicate pending/failed vectorization

            return file_id
        finally:
            conn.close()

    @staticmethod
    def delete_file(kb_id: int, file_id: int) -> None:
        """Delete a file from knowledge base and its vectors"""
        conn = sqlite3.connect('db/db.sqlite')
        cursor = conn.cursor()

        try:
            # Get km_id
            cursor.execute("SELECT km_id FROM km_cfg WHERE id = ?", (kb_id,))
            row = cursor.fetchone()
            if row:
                km_id_str = row[0]

                # Delete from vector database
                try:
                    vector_service = get_vector_service()
                    vector_service.delete_document(km_id_str, file_id)
                except Exception as e:
                    logger.error(f"Error deleting vectors for file {file_id}: {e}")

            # Hard delete from database
            from db.write_queue import db_write
            from sqlalchemy import text as sa_text
            _fid = file_id
            def _do(session):
                session.execute(sa_text("DELETE FROM km_data WHERE id = :fid"), {"fid": _fid})
            db_write(_do, description="km_service_delete_file")
        finally:
            conn.close()

    @staticmethod
    def vector_search(kb_id: int, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Perform vector search using ChromaDB and OpenAI"""
        conn = sqlite3.connect('db/db.sqlite')
        cursor = conn.cursor()

        try:
            # Get km_id
            cursor.execute("SELECT km_id FROM km_cfg WHERE id = ?", (kb_id,))
            row = cursor.fetchone()
            if not row:
                raise ValueError(f"Knowledge base {kb_id} not found")

            km_id_str = row[0]

            # Perform vector search
            vector_service = get_vector_service()
            results = vector_service.search(km_id_str, query, top_k)

            return results

        except Exception as e:
            logger.error(f"Error performing vector search: {e}")
            raise
        finally:
            conn.close()

    @staticmethod
    def get_key_values(kb_id: int) -> List[Dict[str, Any]]:
        """Get all key-value pairs for a knowledge base"""
        conn = sqlite3.connect('db/db.sqlite')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            # Get km_id string from km_cfg
            cursor.execute("SELECT km_id FROM km_cfg WHERE id = ?", (kb_id,))
            row = cursor.fetchone()
            if not row:
                return []

            km_id_str = row['km_id']

            # Query key_value using km_id string
            cursor.execute("""
                SELECT id, key, value, km_id
                FROM key_value
                WHERE km_id = ?
                ORDER BY key
            """, (km_id_str,))

            kvs = []
            for row in cursor.fetchall():
                kvs.append({
                    "id": row['id'],
                    "key": row['key'],
                    "value": row['value'],
                    "km_id": row['km_id']
                })

            return kvs
        finally:
            conn.close()

    @staticmethod
    def add_key_value(kb_id: int, key: str, value: str) -> int:
        """Add a key-value pair"""
        conn = sqlite3.connect('db/db.sqlite')
        cursor = conn.cursor()

        try:
            # Get km_id string from km_cfg
            cursor.execute("SELECT km_id FROM km_cfg WHERE id = ?", (kb_id,))
            row = cursor.fetchone()
            if not row:
                raise ValueError(f"Knowledge base {kb_id} not found")

            km_id_str = row[0]

            from db.write_queue import db_write
            from sqlalchemy import text as sa_text
            _key = key
            _value = value
            _km_id = km_id_str
            def _do(session):
                session.execute(sa_text(
                    "INSERT INTO key_value (key, value, km_id) VALUES (:key, :value, :km_id)"
                ), {"key": _key, "value": _value, "km_id": _km_id})
                session.flush()
                return session.execute(sa_text("SELECT last_insert_rowid()")).scalar()
            kv_id = db_write(_do, description="km_service_add_kv")

            return kv_id
        finally:
            conn.close()

    @staticmethod
    def update_key_value(kb_id: int, kv_id: int, key: str, value: str) -> None:
        """Update a key-value pair"""
        conn = sqlite3.connect('db/db.sqlite')
        cursor = conn.cursor()

        try:
            # Get km_id string from km_cfg
            cursor.execute("SELECT km_id FROM km_cfg WHERE id = ?", (kb_id,))
            row = cursor.fetchone()
            if not row:
                raise ValueError(f"Knowledge base {kb_id} not found")

            km_id_str = row[0]

            from db.write_queue import db_write
            from sqlalchemy import text as sa_text
            _key = key
            _value = value
            _kv_id = kv_id
            _km_id = km_id_str
            def _do(session):
                session.execute(sa_text(
                    "UPDATE key_value SET key = :key, value = :value WHERE id = :kv_id AND km_id = :km_id"
                ), {"key": _key, "value": _value, "kv_id": _kv_id, "km_id": _km_id})
            db_write(_do, description="km_service_update_kv")
        finally:
            conn.close()

    @staticmethod
    def delete_key_value(kb_id: int, kv_id: int) -> None:
        """Delete a key-value pair"""
        conn = sqlite3.connect('db/db.sqlite')
        cursor = conn.cursor()

        try:
            # Get km_id string from km_cfg
            cursor.execute("SELECT km_id FROM km_cfg WHERE id = ?", (kb_id,))
            row = cursor.fetchone()
            if not row:
                raise ValueError(f"Knowledge base {kb_id} not found")

            km_id_str = row[0]

            from db.write_queue import db_write
            from sqlalchemy import text as sa_text
            _kv_id = kv_id
            _km_id = km_id_str
            def _do(session):
                session.execute(sa_text(
                    "DELETE FROM key_value WHERE id = :kv_id AND km_id = :km_id"
                ), {"kv_id": _kv_id, "km_id": _km_id})
            db_write(_do, description="km_service_delete_kv")
        finally:
            conn.close()
