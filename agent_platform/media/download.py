"""
File Download Handler

Provides file download and serving functionality.
"""

import os
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
import aiofiles
import mimetypes

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


download_router = APIRouter(prefix="/api/v1/files", tags=["Files"])


class FileDownloader:
    """
    File Downloader

    Handles file downloads with:
    - Streaming support for large files
    - Range requests for resumable downloads
    - Access tracking
    """

    def __init__(self, upload_dir: str = "uploads"):
        """
        Initialize file downloader.

        Args:
            upload_dir: Directory containing uploaded files
        """
        self.upload_dir = upload_dir

    def get_file_info(self, file_id: str) -> Optional[dict]:
        """Get file information"""
        from db.database import SessionLocal
        from db.models.platform_models import FileUpload

        db = SessionLocal()
        try:
            file_record = db.query(FileUpload).filter(
                FileUpload.file_id == file_id
            ).first()

            if not file_record:
                return None

            # Check expiration
            if file_record.expires_at and file_record.expires_at < datetime.now():
                return None

            if file_record.status != "active":
                return None

            return {
                "file_id": file_record.file_id,
                "original_name": file_record.original_name,
                "file_path": file_record.file_path,
                "file_size": file_record.file_size,
                "mime_type": file_record.mime_type,
                "created_at": file_record.created_at,
                "expires_at": file_record.expires_at
            }
        finally:
            db.close()

    def update_access(self, file_id: str):
        """Update file access stats"""
        from db.database import SessionLocal
        from db.models.platform_models import FileUpload

        db = SessionLocal()
        try:
            file_record = db.query(FileUpload).filter(
                FileUpload.file_id == file_id
            ).first()

            if file_record:
                from db.write_queue import db_write
                _fid = file_id
                def _do(session):
                    rec = session.query(FileUpload).filter(FileUpload.file_id == _fid).first()
                    if rec:
                        rec.download_count += 1
                        rec.last_accessed_at = datetime.now()
                db_write(_do, description="media_update_download_stats")
        finally:
            db.close()

    async def stream_file(self, file_path: str, chunk_size: int = 8192):
        """Stream file content"""
        async with aiofiles.open(file_path, 'rb') as f:
            while chunk := await f.read(chunk_size):
                yield chunk

    def get_file_response(
        self,
        file_id: str,
        inline: bool = False
    ) -> FileResponse:
        """
        Get file response for download.

        Args:
            file_id: File ID
            inline: If True, display inline instead of download

        Returns:
            FileResponse for the file
        """
        file_info = self.get_file_info(file_id)
        if not file_info:
            raise HTTPException(status_code=404, detail="File not found")

        file_path = file_info["file_path"]
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="File not found on disk")

        # Update access
        self.update_access(file_id)

        # Determine content disposition
        disposition = "inline" if inline else "attachment"

        return FileResponse(
            path=file_path,
            filename=file_info["original_name"],
            media_type=file_info["mime_type"],
            headers={
                "Content-Disposition": f'{disposition}; filename="{file_info["original_name"]}"'
            }
        )


# Singleton instance
_file_downloader: Optional[FileDownloader] = None


def get_file_downloader() -> FileDownloader:
    """Get the file downloader instance"""
    global _file_downloader
    if _file_downloader is None:
        _file_downloader = FileDownloader()
    return _file_downloader


@download_router.get("/{file_id}")
async def download_file(file_id: str, inline: bool = False):
    """
    Download a file.

    Args:
        file_id: File ID
        inline: If true, display inline (for images/PDFs)
    """
    downloader = get_file_downloader()
    return downloader.get_file_response(file_id, inline)


@download_router.get("/{file_id}/info")
async def get_file_info(file_id: str):
    """Get file information"""
    downloader = get_file_downloader()
    info = downloader.get_file_info(file_id)

    if not info:
        raise HTTPException(status_code=404, detail="File not found")

    return info


@download_router.delete("/{file_id}")
async def delete_file(file_id: str):
    """Delete a file"""
    from agent_platform.media.upload import get_file_uploader

    uploader = get_file_uploader()
    if uploader.delete_file(file_id):
        return {"success": True, "message": "File deleted"}
    else:
        raise HTTPException(status_code=404, detail="File not found")
