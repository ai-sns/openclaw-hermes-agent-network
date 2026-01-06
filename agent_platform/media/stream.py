"""
Media Stream Handler

Provides streaming for media files.
"""

import os
from typing import Optional, AsyncGenerator
import aiofiles


class MediaStreamHandler:
    """
    Media Stream Handler

    Handles streaming of media files for:
    - Video streaming
    - Audio streaming
    - Large file downloads
    """

    def __init__(self, chunk_size: int = 65536):
        """
        Initialize stream handler.

        Args:
            chunk_size: Size of each chunk in bytes
        """
        self.chunk_size = chunk_size

    async def stream_file(
        self,
        file_path: str,
        start: int = 0,
        end: Optional[int] = None
    ) -> AsyncGenerator[bytes, None]:
        """
        Stream file content.

        Args:
            file_path: Path to file
            start: Start byte position
            end: End byte position (None = end of file)

        Yields:
            File chunks
        """
        file_size = os.path.getsize(file_path)

        if end is None:
            end = file_size - 1

        async with aiofiles.open(file_path, 'rb') as f:
            await f.seek(start)
            remaining = end - start + 1

            while remaining > 0:
                chunk_size = min(self.chunk_size, remaining)
                chunk = await f.read(chunk_size)
                if not chunk:
                    break
                remaining -= len(chunk)
                yield chunk

    def parse_range_header(
        self,
        range_header: str,
        file_size: int
    ) -> tuple:
        """
        Parse HTTP Range header.

        Args:
            range_header: Range header value (e.g., "bytes=0-1023")
            file_size: Total file size

        Returns:
            Tuple of (start, end)
        """
        if not range_header or not range_header.startswith("bytes="):
            return 0, file_size - 1

        try:
            range_spec = range_header[6:]  # Remove "bytes="
            if range_spec.startswith("-"):
                # Last N bytes
                end = file_size - 1
                start = file_size - int(range_spec[1:])
            elif range_spec.endswith("-"):
                # From start to end
                start = int(range_spec[:-1])
                end = file_size - 1
            else:
                # Start-End
                parts = range_spec.split("-")
                start = int(parts[0])
                end = int(parts[1])

            # Validate
            start = max(0, start)
            end = min(end, file_size - 1)

            return start, end
        except:
            return 0, file_size - 1


# Singleton instance
_media_stream_handler: Optional[MediaStreamHandler] = None


def get_media_stream_handler() -> MediaStreamHandler:
    """Get media stream handler instance"""
    global _media_stream_handler
    if _media_stream_handler is None:
        _media_stream_handler = MediaStreamHandler()
    return _media_stream_handler
