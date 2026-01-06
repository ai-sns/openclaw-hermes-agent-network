"""
File Upload Handler

Provides file upload functionality with local storage.
"""

import os
import uuid
import hashlib
import aiofiles
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from dataclasses import dataclass
from fastapi import UploadFile
import mimetypes

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


@dataclass
class UploadResult:
    """Upload result data structure"""
    file_id: str
    original_name: str
    stored_name: str
    file_path: str
    file_size: int
    mime_type: Optional[str]
    file_hash: str
    download_url: str
    created_at: datetime
    expires_at: Optional[datetime]


class FileUploader:
    """
    File Uploader

    Handles file uploads with:
    - Local storage
    - Hash verification
    - Expiration support
    - MIME type detection
    """

    def __init__(
        self,
        upload_dir: str = "uploads",
        max_file_size: int = 100 * 1024 * 1024,  # 100MB
        base_url: str = "/api/v1/files"
    ):
        """
        Initialize file uploader.

        Args:
            upload_dir: Directory for uploaded files
            max_file_size: Maximum file size in bytes
            base_url: Base URL for download links
        """
        self.upload_dir = upload_dir
        self.max_file_size = max_file_size
        self.base_url = base_url

        # Ensure upload directory exists
        os.makedirs(upload_dir, exist_ok=True)

    def _generate_file_id(self) -> str:
        """Generate unique file ID"""
        return f"file_{uuid.uuid4().hex}"

    def _get_stored_name(self, file_id: str, original_name: str) -> str:
        """Generate stored filename"""
        ext = os.path.splitext(original_name)[1] if original_name else ""
        return f"{file_id}{ext}"

    def _detect_mime_type(self, filename: str) -> Optional[str]:
        """Detect MIME type from filename"""
        mime_type, _ = mimetypes.guess_type(filename)
        return mime_type

    async def _calculate_hash(self, file_path: str) -> str:
        """Calculate SHA256 hash of file"""
        sha256 = hashlib.sha256()
        async with aiofiles.open(file_path, 'rb') as f:
            while chunk := await f.read(8192):
                sha256.update(chunk)
        return sha256.hexdigest()

    async def upload(
        self,
        file: UploadFile,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        expires_in_hours: int = 24
    ) -> UploadResult:
        """
        Upload a file.

        Args:
            file: FastAPI UploadFile
            user_id: Owner user ID
            session_id: Associated session ID
            expires_in_hours: File expiration time

        Returns:
            UploadResult with file information
        """
        # Generate IDs
        file_id = self._generate_file_id()
        original_name = file.filename or "unknown"
        stored_name = self._get_stored_name(file_id, original_name)
        file_path = os.path.join(self.upload_dir, stored_name)

        # Save file
        file_size = 0
        async with aiofiles.open(file_path, 'wb') as out_file:
            while chunk := await file.read(8192):
                file_size += len(chunk)
                if file_size > self.max_file_size:
                    # Clean up and raise error
                    await out_file.close()
                    os.remove(file_path)
                    raise ValueError(f"File too large. Max size: {self.max_file_size} bytes")
                await out_file.write(chunk)

        # Calculate hash
        file_hash = await self._calculate_hash(file_path)

        # Detect MIME type
        mime_type = self._detect_mime_type(original_name)

        # Calculate expiration
        expires_at = datetime.now() + timedelta(hours=expires_in_hours)

        # Generate download URL
        download_url = f"{self.base_url}/{file_id}"

        # Save to database
        from db.database import SessionLocal
        from db.models.platform_models import FileUpload as FileUploadModel

        db = SessionLocal()
        try:
            db_file = FileUploadModel(
                file_id=file_id,
                original_name=original_name,
                stored_name=stored_name,
                file_path=file_path,
                file_size=file_size,
                mime_type=mime_type,
                file_hash=file_hash,
                user_id=user_id,
                session_id=session_id,
                status="active",
                expires_at=expires_at
            )
            db.add(db_file)
            db.commit()
        finally:
            db.close()

        return UploadResult(
            file_id=file_id,
            original_name=original_name,
            stored_name=stored_name,
            file_path=file_path,
            file_size=file_size,
            mime_type=mime_type,
            file_hash=file_hash,
            download_url=download_url,
            created_at=datetime.now(),
            expires_at=expires_at
        )

    async def upload_from_bytes(
        self,
        content: bytes,
        filename: str,
        user_id: Optional[str] = None,
        expires_in_hours: int = 24
    ) -> UploadResult:
        """
        Upload from bytes.

        Args:
            content: File content as bytes
            filename: Original filename
            user_id: Owner user ID
            expires_in_hours: Expiration time

        Returns:
            UploadResult
        """
        if len(content) > self.max_file_size:
            raise ValueError(f"File too large. Max size: {self.max_file_size} bytes")

        file_id = self._generate_file_id()
        stored_name = self._get_stored_name(file_id, filename)
        file_path = os.path.join(self.upload_dir, stored_name)

        # Write file
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(content)

        # Calculate hash
        file_hash = hashlib.sha256(content).hexdigest()
        mime_type = self._detect_mime_type(filename)
        expires_at = datetime.now() + timedelta(hours=expires_in_hours)
        download_url = f"{self.base_url}/{file_id}"

        # Save to database
        from db.database import SessionLocal
        from db.models.platform_models import FileUpload as FileUploadModel

        db = SessionLocal()
        try:
            db_file = FileUploadModel(
                file_id=file_id,
                original_name=filename,
                stored_name=stored_name,
                file_path=file_path,
                file_size=len(content),
                mime_type=mime_type,
                file_hash=file_hash,
                user_id=user_id,
                status="active",
                expires_at=expires_at
            )
            db.add(db_file)
            db.commit()
        finally:
            db.close()

        return UploadResult(
            file_id=file_id,
            original_name=filename,
            stored_name=stored_name,
            file_path=file_path,
            file_size=len(content),
            mime_type=mime_type,
            file_hash=file_hash,
            download_url=download_url,
            created_at=datetime.now(),
            expires_at=expires_at
        )

    def get_file_path(self, file_id: str) -> Optional[str]:
        """Get file path by ID"""
        from db.database import SessionLocal
        from db.models.platform_models import FileUpload as FileUploadModel

        db = SessionLocal()
        try:
            file_record = db.query(FileUploadModel).filter(
                FileUploadModel.file_id == file_id,
                FileUploadModel.status == "active"
            ).first()

            if not file_record:
                return None

            # Check expiration
            if file_record.expires_at and file_record.expires_at < datetime.now():
                file_record.status = "expired"
                db.commit()
                return None

            return file_record.file_path
        finally:
            db.close()

    def delete_file(self, file_id: str) -> bool:
        """Delete a file"""
        from db.database import SessionLocal
        from db.models.platform_models import FileUpload as FileUploadModel

        db = SessionLocal()
        try:
            file_record = db.query(FileUploadModel).filter(
                FileUploadModel.file_id == file_id
            ).first()

            if not file_record:
                return False

            # Delete physical file
            if os.path.exists(file_record.file_path):
                os.remove(file_record.file_path)

            # Update status
            file_record.status = "deleted"
            file_record.deleted_at = datetime.now()
            db.commit()

            return True
        finally:
            db.close()


# Singleton instance
_file_uploader: Optional[FileUploader] = None


def get_file_uploader() -> FileUploader:
    """Get the file uploader instance"""
    global _file_uploader
    if _file_uploader is None:
        _file_uploader = FileUploader()
    return _file_uploader
