"""
Platform Database Models

SQLAlchemy models for API Gateway and Protocol features.
"""

from datetime import datetime
from typing import Optional, List
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, JSON, Index
from sqlalchemy.orm import relationship
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from db.base_class import Base


class APIKey(Base):
    """API Key for authentication"""
    __tablename__ = 'api_keys'
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    key_hash = Column(String(256), unique=True, index=True, nullable=False, comment="SHA256 hash of API key")
    key_prefix = Column(String(10), nullable=False, comment="First 8 chars of key for identification")
    name = Column(String(100), nullable=False, comment="Human-readable name")
    user_id = Column(String(100), nullable=False, index=True, comment="Owner user ID")
    scopes = Column(JSON, default=list, comment="Permission scopes: ['agent:read', 'task:create', etc.]")
    rate_limit = Column(Integer, default=1000, comment="Requests per minute")
    is_active = Column(Boolean, default=True, comment="Whether key is active")
    created_at = Column(DateTime, default=datetime.now, comment="Creation time")
    last_used_at = Column(DateTime, nullable=True, comment="Last usage time")
    expires_at = Column(DateTime, nullable=True, comment="Expiration time (null = never)")

    # Note: Use __table_args__ at class level for extend_existing

    def __repr__(self):
        return f"<APIKey(name={self.name}, prefix={self.key_prefix})>"


class A2ATask(Base):
    """A2A Protocol Task Record"""
    __tablename__ = 'a2a_tasks'

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(String(50), unique=True, index=True, nullable=False, comment="Unique task ID (UUID)")
    agent_id = Column(String(100), index=True, nullable=False, comment="Target agent ID")
    caller_agent_id = Column(String(100), nullable=True, comment="Caller agent ID (for A2A calls)")
    caller_endpoint = Column(String(500), nullable=True, comment="Caller endpoint URL")

    status = Column(String(20), default='pending', nullable=False,
                   comment="Task status: pending/running/completed/failed/cancelled")
    priority = Column(Integer, default=0, comment="Task priority (higher = more urgent)")

    input_data = Column(JSON, nullable=False, comment="Task input data")
    output_data = Column(JSON, nullable=True, comment="Task output data")
    error_message = Column(Text, nullable=True, comment="Error message if failed")

    webhook_url = Column(String(500), nullable=True, comment="Webhook callback URL")
    webhook_sent = Column(Boolean, default=False, comment="Whether webhook was sent")

    # Task metadata (renamed from 'metadata' to avoid SQLAlchemy conflict)
    task_metadata = Column(JSON, nullable=True, comment="Additional metadata")

    # Timestamps
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    started_at = Column(DateTime, nullable=True, comment="When task started executing")
    completed_at = Column(DateTime, nullable=True, comment="When task completed")

    # Execution stats
    execution_time_ms = Column(Integer, nullable=True, comment="Execution time in milliseconds")
    token_usage = Column(JSON, nullable=True, comment="Token usage stats")

    __table_args__ = (
        Index('idx_a2a_task_status', 'status'),
        Index('idx_a2a_task_agent_status', 'agent_id', 'status'),
        {'extend_existing': True}
    )

    def __repr__(self):
        return f"<A2ATask(id={self.task_id}, status={self.status})>"


class SessionRecord(Base):
    """Session and Thread Management"""
    __tablename__ = 'sessions'

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(50), unique=True, index=True, nullable=False, comment="Session ID (UUID)")
    user_id = Column(String(100), nullable=True, index=True, comment="Associated user ID")
    agent_id = Column(String(100), nullable=True, comment="Primary agent ID")

    # Thread tracking
    thread_id = Column(String(50), nullable=True, comment="Current thread ID")
    thread_count = Column(Integer, default=0, comment="Number of threads in session")

    # Context
    context_data = Column(JSON, default=dict, comment="Session context data")
    messages = Column(JSON, default=list, comment="Conversation messages")
    message_count = Column(Integer, default=0, comment="Total message count")

    # Status
    status = Column(String(20), default='active', comment="Session status: active/paused/closed")

    # Timestamps
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    last_activity_at = Column(DateTime, default=datetime.now, comment="Last activity timestamp")
    expires_at = Column(DateTime, nullable=True, comment="Session expiration time")

    # Session metadata (renamed from 'metadata' to avoid SQLAlchemy conflict)
    session_metadata = Column(JSON, nullable=True, comment="Session metadata")
    client_info = Column(JSON, nullable=True, comment="Client information (IP, User-Agent, etc.)")

    __table_args__ = (
        Index('idx_session_user', 'user_id'),
        Index('idx_session_status', 'status'),
        {'extend_existing': True}
    )

    def __repr__(self):
        return f"<SessionRecord(id={self.session_id}, status={self.status})>"


class WebhookDelivery(Base):
    """Webhook Delivery Log"""
    __tablename__ = 'webhook_deliveries'
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    webhook_id = Column(String(50), unique=True, index=True, nullable=False)
    task_id = Column(String(50), index=True, nullable=False, comment="Related task ID")

    url = Column(String(500), nullable=False, comment="Webhook URL")
    payload = Column(JSON, nullable=False, comment="Request payload")

    # Delivery status
    status = Column(String(20), default='pending', comment="Status: pending/success/failed/retrying")
    attempts = Column(Integer, default=0, comment="Number of delivery attempts")
    max_attempts = Column(Integer, default=3, comment="Maximum retry attempts")

    # Response
    response_status_code = Column(Integer, nullable=True, comment="HTTP response status code")
    response_body = Column(Text, nullable=True, comment="Response body (truncated)")
    error_message = Column(Text, nullable=True, comment="Error message if failed")

    # Timestamps
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    last_attempt_at = Column(DateTime, nullable=True)
    next_retry_at = Column(DateTime, nullable=True)
    delivered_at = Column(DateTime, nullable=True)

    def __repr__(self):
        return f"<WebhookDelivery(id={self.webhook_id}, status={self.status})>"


class FileUpload(Base):
    """File Upload Record"""
    __tablename__ = 'file_uploads'
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    file_id = Column(String(50), unique=True, index=True, nullable=False, comment="File ID (UUID)")

    # File info
    original_name = Column(String(255), nullable=False, comment="Original filename")
    stored_name = Column(String(255), nullable=False, comment="Stored filename")
    file_path = Column(String(500), nullable=False, comment="Full file path")
    file_size = Column(Integer, nullable=False, comment="File size in bytes")
    mime_type = Column(String(100), nullable=True, comment="MIME type")
    file_hash = Column(String(64), nullable=True, comment="SHA256 hash of file")

    # Ownership
    user_id = Column(String(100), nullable=True, index=True)
    session_id = Column(String(50), nullable=True)

    # Status
    status = Column(String(20), default='active', comment="Status: active/deleted/expired")

    # Timestamps
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    expires_at = Column(DateTime, nullable=True, comment="File expiration time")
    deleted_at = Column(DateTime, nullable=True)

    # Access stats
    download_count = Column(Integer, default=0)
    last_accessed_at = Column(DateTime, nullable=True)

    def __repr__(self):
        return f"<FileUpload(id={self.file_id}, name={self.original_name})>"


class RateLimitRecord(Base):
    """Rate Limit Tracking"""
    __tablename__ = 'rate_limit_records'

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(100), index=True, nullable=False, comment="Rate limit key (API key or IP)")
    endpoint = Column(String(200), nullable=True, comment="Specific endpoint")

    request_count = Column(Integer, default=0, comment="Request count in window")
    window_start = Column(DateTime, nullable=False, comment="Window start time")
    window_seconds = Column(Integer, default=60, comment="Window duration in seconds")

    # Limit info
    limit = Column(Integer, nullable=False, comment="Request limit for window")
    is_blocked = Column(Boolean, default=False, comment="Whether currently blocked")
    blocked_until = Column(DateTime, nullable=True, comment="Block expiration time")

    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    __table_args__ = (
        Index('idx_rate_limit_key_window', 'key', 'window_start'),
        {'extend_existing': True}
    )

    def __repr__(self):
        return f"<RateLimitRecord(key={self.key}, count={self.request_count})>"
