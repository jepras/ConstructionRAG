from typing import Optional, Dict, Any
import traceback
import sys
from datetime import datetime

from src.config.settings import get_settings

# Optional PostHog import - graceful fallback if not available
try:
    from posthog import Posthog
    from posthog.ai.langchain.callbacks import CallbackHandler as PostHogCallbackHandler
    POSTHOG_AVAILABLE = True
except ImportError:
    Posthog = None
    PostHogCallbackHandler = None
    POSTHOG_AVAILABLE = False


class PostHogService:
    """PostHog service for analytics and error tracking."""
    
    _instance: Optional['PostHogService'] = None
    _client: Optional[Any] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """Initialize PostHog client."""
        if not POSTHOG_AVAILABLE:
            return
            
        settings = get_settings()
        
        if settings.posthog_api_key:
            self._client = Posthog(
                project_api_key=settings.posthog_api_key,
                host=settings.posthog_host,
                enable_exception_autocapture=True,
                # Server-side settings for better performance
                flush_at=10,  # Batch up to 10 events
                flush_interval=10,  # Flush every 10 seconds
                timeout=5,  # 5 second timeout
            )
    
    def is_enabled(self) -> bool:
        """Check if PostHog is configured and enabled."""
        return POSTHOG_AVAILABLE and self._client is not None
    
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
    
    def get_langchain_callback(
        self,
        pipeline_step: Optional[str] = None,
        indexing_run_id: Optional[str] = None,
        user_id: Optional[str] = None,
        additional_properties: Optional[Dict[str, Any]] = None
    ) -> Optional[Any]:
        """Get a PostHog LangChain callback handler for automatic LLM tracking.
        
        Args:
            pipeline_step: Name of the pipeline step (e.g., 'wiki_overview_generation')
            indexing_run_id: ID of the indexing run for correlation
            user_id: Optional user ID for tracking
            additional_properties: Additional properties to include in events
            
        Returns:
            PostHog CallbackHandler instance or None if PostHog is not available
        """
        if not self.is_enabled() or not PostHogCallbackHandler:
            return None
            
        # Build properties for the callback
        properties = {
            "pipeline_step": pipeline_step,
            "environment": get_settings().environment,
        }
        
        if additional_properties:
            properties.update(additional_properties)
        
        # Use indexing_run_id as both distinct_id and trace_id for correlation
        distinct_id = user_id or indexing_run_id or f"backend-{hash(sys.argv[0])}"
        
        try:
            return PostHogCallbackHandler(
                client=self._client,
                distinct_id=distinct_id,
                trace_id=indexing_run_id,
                properties=properties,
                privacy_mode=False,  # We want full prompt/response tracking
                groups={"indexing_run": indexing_run_id} if indexing_run_id else None
            )
        except Exception as e:
            # Log but don't fail - analytics should never break the pipeline
            print(f"Warning: Could not create PostHog callback: {e}")
            return None
    
    def shutdown(self) -> None:
        """Flush and shutdown PostHog client."""
        if self._client:
            try:
                self._client.shutdown()
            except Exception:
                pass


# Global instance
posthog_service = PostHogService()