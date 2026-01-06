"""
Rate Limiter Middleware

Implements token bucket rate limiting for API requests.
"""

import time
import asyncio
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional, Dict, Tuple
from datetime import datetime
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import logging

logger = logging.getLogger(__name__)


@dataclass
class RateLimitBucket:
    """Token bucket for rate limiting"""
    tokens: float
    last_update: float
    rate: int  # tokens per window
    window: int  # window in seconds
    blocked_until: Optional[float] = None


class RateLimiter:
    """
    Token Bucket Rate Limiter

    Implements a token bucket algorithm for rate limiting.
    Tokens are replenished at a steady rate.
    """

    def __init__(self, default_rate: int = 100, default_window: int = 60):
        """
        Initialize rate limiter.

        Args:
            default_rate: Default requests per window
            default_window: Default window in seconds
        """
        self.default_rate = default_rate
        self.default_window = default_window
        self.buckets: Dict[str, RateLimitBucket] = {}
        self._lock = asyncio.Lock()

    def _get_bucket(self, key: str, rate: Optional[int] = None, window: Optional[int] = None) -> RateLimitBucket:
        """Get or create a bucket for the key"""
        if key not in self.buckets:
            self.buckets[key] = RateLimitBucket(
                tokens=rate or self.default_rate,
                last_update=time.time(),
                rate=rate or self.default_rate,
                window=window or self.default_window
            )
        return self.buckets[key]

    def _replenish_tokens(self, bucket: RateLimitBucket) -> None:
        """Replenish tokens based on time elapsed"""
        now = time.time()
        elapsed = now - bucket.last_update
        bucket.last_update = now

        # Calculate tokens to add
        tokens_to_add = elapsed * (bucket.rate / bucket.window)
        bucket.tokens = min(bucket.rate, bucket.tokens + tokens_to_add)

    async def check_rate_limit(
        self,
        key: str,
        rate: Optional[int] = None,
        window: Optional[int] = None,
        cost: int = 1
    ) -> Tuple[bool, Dict[str, any]]:
        """
        Check if request is within rate limit.

        Args:
            key: Rate limit key (e.g., API key, IP address)
            rate: Custom rate limit
            window: Custom window
            cost: Token cost for this request

        Returns:
            Tuple of (is_allowed, info_dict)
        """
        async with self._lock:
            bucket = self._get_bucket(key, rate, window)

            # Check if blocked
            if bucket.blocked_until and time.time() < bucket.blocked_until:
                return False, {
                    "remaining": 0,
                    "limit": bucket.rate,
                    "reset": int(bucket.blocked_until),
                    "retry_after": int(bucket.blocked_until - time.time())
                }

            # Replenish tokens
            self._replenish_tokens(bucket)

            # Check if enough tokens
            if bucket.tokens >= cost:
                bucket.tokens -= cost
                return True, {
                    "remaining": int(bucket.tokens),
                    "limit": bucket.rate,
                    "reset": int(time.time() + bucket.window)
                }
            else:
                # Block for a short period if too many requests
                bucket.blocked_until = time.time() + 5  # 5 second cooldown
                return False, {
                    "remaining": 0,
                    "limit": bucket.rate,
                    "reset": int(bucket.blocked_until),
                    "retry_after": 5
                }

    def get_remaining(self, key: str) -> int:
        """Get remaining tokens for a key"""
        if key not in self.buckets:
            return self.default_rate

        bucket = self.buckets[key]
        self._replenish_tokens(bucket)
        return int(bucket.tokens)

    def reset_bucket(self, key: str) -> None:
        """Reset a rate limit bucket"""
        if key in self.buckets:
            del self.buckets[key]


class RateLimiterMiddleware(BaseHTTPMiddleware):
    """
    FastAPI Rate Limiter Middleware

    Applies rate limiting based on API key or IP address.
    """

    def __init__(
        self,
        app,
        rate: int = 100,
        per: int = 60,
        exempt_paths: Optional[list] = None
    ):
        """
        Initialize middleware.

        Args:
            app: FastAPI app
            rate: Requests per window
            per: Window in seconds
            exempt_paths: Paths exempt from rate limiting
        """
        super().__init__(app)
        self.rate_limiter = RateLimiter(default_rate=rate, default_window=per)
        self.exempt_paths = exempt_paths or ["/health", "/docs", "/openapi.json"]

    def _get_rate_limit_key(self, request: Request) -> str:
        """Get rate limit key from request"""
        # Use API key if available
        if hasattr(request.state, "api_key_info"):
            return f"api:{request.state.api_key_info.key_prefix}"

        # Fall back to IP address
        client_ip = request.client.host if request.client else "unknown"
        return f"ip:{client_ip}"

    def _get_rate_limit(self, request: Request) -> int:
        """Get rate limit for request"""
        # Use API key rate limit if available
        if hasattr(request.state, "api_key_info"):
            return request.state.api_key_info.rate_limit

        # Default rate limit for unauthenticated requests
        return 60  # More restrictive for non-authenticated

    async def dispatch(self, request: Request, call_next):
        """Process request through rate limiter"""
        path = request.url.path

        # Skip rate limiting for exempt paths
        if path in self.exempt_paths or request.method == "OPTIONS":
            return await call_next(request)

        # Get rate limit key and limit
        key = self._get_rate_limit_key(request)
        rate = self._get_rate_limit(request)

        # Check rate limit
        allowed, info = await self.rate_limiter.check_rate_limit(key, rate=rate)

        if not allowed:
            logger.warning(f"Rate limit exceeded for {key}")
            response = JSONResponse(
                status_code=429,
                content={
                    "success": False,
                    "error": "Rate limit exceeded",
                    "error_code": "RATE_LIMIT_EXCEEDED",
                    "retry_after": info.get("retry_after", 60)
                }
            )
            # Add rate limit headers
            response.headers["X-RateLimit-Limit"] = str(info["limit"])
            response.headers["X-RateLimit-Remaining"] = str(info["remaining"])
            response.headers["X-RateLimit-Reset"] = str(info["reset"])
            response.headers["Retry-After"] = str(info.get("retry_after", 60))
            return response

        # Continue with request
        response = await call_next(request)

        # Add rate limit headers to response
        response.headers["X-RateLimit-Limit"] = str(info["limit"])
        response.headers["X-RateLimit-Remaining"] = str(info["remaining"])
        response.headers["X-RateLimit-Reset"] = str(info["reset"])

        return response


# Singleton instance
_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    """Get the singleton rate limiter instance"""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter


async def check_rate_limit(
    request: Request,
    cost: int = 1
) -> Dict[str, any]:
    """
    Dependency to check rate limit.

    Usage:
        @app.get("/expensive")
        async def expensive_endpoint(
            rate_info: dict = Depends(lambda r: check_rate_limit(r, cost=5))
        ):
            ...
    """
    limiter = get_rate_limiter()

    # Get key
    if hasattr(request.state, "api_key_info"):
        key = f"api:{request.state.api_key_info.key_prefix}"
        rate = request.state.api_key_info.rate_limit
    else:
        key = f"ip:{request.client.host if request.client else 'unknown'}"
        rate = 60

    allowed, info = await limiter.check_rate_limit(key, rate=rate, cost=cost)

    if not allowed:
        raise HTTPException(
            status_code=429,
            detail={
                "error": "Rate limit exceeded",
                "error_code": "RATE_LIMIT_EXCEEDED",
                "retry_after": info.get("retry_after", 60)
            }
        )

    return info
