"""Rate limiting middleware for API endpoints."""

import os
import time
from collections import defaultdict, deque
from typing import Dict, Optional, Tuple

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

# Configuration from environment variables
RATE_LIMIT_ENABLED = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"
RATE_LIMIT_ANONYMOUS = int(os.getenv("RATE_LIMIT_ANONYMOUS", "50"))  # PDFs per hour
RATE_LIMIT_AUTHENTICATED = int(os.getenv("RATE_LIMIT_AUTHENTICATED", "0"))  # 0 = unlimited

# Whitelist configuration
WHITELISTED_IPS = {
    "127.0.0.1",
    "localhost",
    "::1",  # IPv6 localhost
    "0.0.0.0",
}

# Add additional IPs from environment
additional_ips = os.getenv("RATE_LIMIT_WHITELIST", "").strip()
if additional_ips:
    WHITELISTED_IPS.update(ip.strip() for ip in additional_ips.split(",") if ip.strip())


class RateLimiter:
    """In-memory rate limiter using sliding window algorithm."""
    
    def __init__(self):
        # Store request timestamps per IP
        # Format: {ip: deque([(timestamp, count), ...])}
        self.requests: Dict[str, deque] = defaultdict(deque)
        
        # Window size in seconds (1 hour)
        self.window_size = 3600
        
        # Cleanup old entries every N requests
        self.cleanup_counter = 0
        self.cleanup_interval = 100
    
    def _cleanup_old_entries(self, ip: str, current_time: float):
        """Remove entries older than the window size."""
        if ip not in self.requests:
            return
        
        window_start = current_time - self.window_size
        
        # Remove old entries from the left side of deque
        while self.requests[ip] and self.requests[ip][0][0] < window_start:
            self.requests[ip].popleft()
        
        # Remove empty deques to save memory
        if not self.requests[ip]:
            del self.requests[ip]
    
    def _periodic_cleanup(self, current_time: float):
        """Periodically clean up all IPs to prevent memory growth."""
        self.cleanup_counter += 1
        
        if self.cleanup_counter >= self.cleanup_interval:
            self.cleanup_counter = 0
            
            # Clean up all IPs
            ips_to_delete = []
            window_start = current_time - self.window_size
            
            for ip, timestamps in list(self.requests.items()):
                # Remove old entries
                while timestamps and timestamps[0][0] < window_start:
                    timestamps.popleft()
                
                # Mark empty deques for deletion
                if not timestamps:
                    ips_to_delete.append(ip)
            
            # Delete empty entries
            for ip in ips_to_delete:
                del self.requests[ip]
    
    def check_rate_limit(
        self,
        ip: str,
        file_count: int = 1,
        is_authenticated: bool = False,
    ) -> Tuple[bool, Optional[Dict[str, any]]]:
        """
        Check if request is within rate limits.
        
        Args:
            ip: Client IP address
            file_count: Number of files in this request
            is_authenticated: Whether user is authenticated
            
        Returns:
            Tuple of (is_allowed, rate_limit_info)
        """
        current_time = time.time()
        
        # Periodic cleanup
        self._periodic_cleanup(current_time)
        
        # Skip rate limiting if disabled
        if not RATE_LIMIT_ENABLED:
            return True, {"enabled": False}
        
        # Skip for whitelisted IPs
        if ip in WHITELISTED_IPS:
            return True, {"whitelisted": True}
        
        # Skip or use higher limit for authenticated users
        if is_authenticated:
            if RATE_LIMIT_AUTHENTICATED == 0:  # Unlimited
                return True, {"authenticated": True, "unlimited": True}
            limit = RATE_LIMIT_AUTHENTICATED
        else:
            limit = RATE_LIMIT_ANONYMOUS
        
        # Clean up old entries for this IP
        self._cleanup_old_entries(ip, current_time)
        
        # Count requests in the current window
        window_start = current_time - self.window_size
        total_files = sum(
            count for timestamp, count in self.requests[ip]
            if timestamp >= window_start
        )
        
        # Check if adding these files would exceed the limit
        if total_files + file_count > limit:
            # Calculate when the oldest request will expire
            if self.requests[ip]:
                oldest_timestamp = self.requests[ip][0][0]
                reset_time = oldest_timestamp + self.window_size
                retry_after = int(reset_time - current_time)
            else:
                retry_after = 0
            
            return False, {
                "limit": limit,
                "current": total_files,
                "requested": file_count,
                "retry_after_seconds": max(0, retry_after),
                "window_minutes": self.window_size // 60,
            }
        
        # Add the new request
        self.requests[ip].append((current_time, file_count))
        
        return True, {
            "limit": limit,
            "used": total_files + file_count,
            "remaining": limit - (total_files + file_count),
            "window_minutes": self.window_size // 60,
        }
    
    def reset_ip(self, ip: str):
        """Reset rate limit for a specific IP (useful for testing)."""
        if ip in self.requests:
            del self.requests[ip]
    
    def reset_all(self):
        """Reset all rate limits (useful for testing)."""
        self.requests.clear()


# Global rate limiter instance
rate_limiter = RateLimiter()


def get_client_ip(request: Request) -> str:
    """Extract client IP from request, handling proxies."""
    # Check for proxy headers (in order of preference)
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # Take the first IP if multiple are present
        return forwarded.split(",")[0].strip()
    
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
    # Fall back to direct connection
    if request.client:
        return request.client.host
    
    return "unknown"


async def rate_limit_middleware(
    request: Request,
    file_count: int = 1,
    is_authenticated: bool = False,
) -> Optional[JSONResponse]:
    """
    Rate limiting middleware for FastAPI.
    
    Args:
        request: FastAPI request object
        file_count: Number of files being uploaded
        is_authenticated: Whether the user is authenticated
        
    Returns:
        None if allowed, JSONResponse with 429 error if rate limited
    """
    client_ip = get_client_ip(request)
    
    allowed, info = rate_limiter.check_rate_limit(
        ip=client_ip,
        file_count=file_count,
        is_authenticated=is_authenticated,
    )
    
    if not allowed:
        # Add rate limit headers
        headers = {
            "X-RateLimit-Limit": str(info["limit"]),
            "X-RateLimit-Remaining": "0",
            "X-RateLimit-Reset": str(int(time.time()) + info["retry_after_seconds"]),
            "Retry-After": str(info["retry_after_seconds"]),
        }
        
        raise HTTPException(
            status_code=429,
            detail={
                "error": "Rate limit exceeded",
                "message": f"You have exceeded the rate limit of {info['limit']} PDFs per hour. Please try again in {info['retry_after_seconds']} seconds.",
                "limit": info["limit"],
                "retry_after": info["retry_after_seconds"],
            },
            headers=headers,
        )
    
    # Add rate limit info headers for successful requests
    if info and "remaining" in info:
        request.state.rate_limit_headers = {
            "X-RateLimit-Limit": str(info["limit"]),
            "X-RateLimit-Remaining": str(info["remaining"]),
            "X-RateLimit-Used": str(info["used"]),
        }
    
    return None


def add_rate_limit_headers(response: JSONResponse, request: Request) -> JSONResponse:
    """Add rate limit headers to response if available."""
    if hasattr(request.state, "rate_limit_headers"):
        for header, value in request.state.rate_limit_headers.items():
            response.headers[header] = value
    return response