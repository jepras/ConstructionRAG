import posthog
from typing import Optional, Dict, Any
import traceback
import sys

from src.config.settings import get_settings


class PostHogService:
    """PostHog service for analytics and error tracking."""
    
    _instance: Optional['PostHogService'] = None
    _client: Optional[posthog.Client] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """Initialize PostHog client."""
        settings = get_settings()
        
        if settings.posthog_api_key:
            self._client = posthog.Client(
                api_key=settings.posthog_api_key,
                host=settings.posthog_host,
                # Server-side settings for better performance
                flush_at=1,  # Send immediately
                flush_interval=0,  # Don't wait
                timeout=5,  # 5 second timeout
            )
    
    def is_enabled(self) -> bool:
        """Check if PostHog is configured and enabled."""
        return self._client is not None
    
    def capture_exception(
        self, 
        exception: Exception,
        user_id: Optional[str] = None,
        properties: Optional[Dict[str, Any]] = None
    ) -> None:
        """Capture an exception with context."""
        if not self.is_enabled():
            return
            
        # Build exception properties
        exc_properties = {
            "error": str(exception),
            "error_type": type(exception).__name__,
            "error_module": getattr(exception, "__module__", "unknown"),
        }
        
        # Add stack trace in development
        settings = get_settings()
        if settings.environment == "development":
            exc_properties["stack_trace"] = "".join(traceback.format_exception(
                type(exception), exception, exception.__traceback__
            ))
        
        # Merge with additional properties
        if properties:
            exc_properties.update(properties)
        
        # Use distinct_id for anonymous tracking if no user_id
        distinct_id = user_id or f"backend-{hash(sys.argv[0])}"
        
        try:
            self._client.capture(
                distinct_id=distinct_id,
                event="$exception",
                properties=exc_properties
            )
        except Exception:
            # Silently fail - don't let error tracking break the app
            pass
    
    def capture_event(
        self,
        event_name: str,
        user_id: Optional[str] = None,
        properties: Optional[Dict[str, Any]] = None
    ) -> None:
        """Capture a custom event."""
        if not self.is_enabled():
            return
            
        distinct_id = user_id or f"backend-{hash(sys.argv[0])}"
        
        try:
            self._client.capture(
                distinct_id=distinct_id,
                event=event_name,
                properties=properties or {}
            )
        except Exception:
            # Silently fail
            pass
    
    def shutdown(self) -> None:
        """Flush and shutdown PostHog client."""
        if self._client:
            try:
                self._client.shutdown()
            except Exception:
                pass


# Global instance
posthog_service = PostHogService()