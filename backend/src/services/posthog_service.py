from typing import Optional, Dict, Any
import traceback
import sys
import time
import uuid
from datetime import datetime

from src.config.settings import get_settings

# Optional PostHog import - graceful fallback if not available
try:
    import posthog
    POSTHOG_AVAILABLE = True
except ImportError:
    posthog = None
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
    
    def capture_llm_generation(
        self,
        model: str,
        input_prompt: str,
        output_content: str,
        latency_ms: float,
        pipeline_step: Optional[str] = None,
        indexing_run_id: Optional[str] = None,
        user_id: Optional[str] = None,
        additional_properties: Optional[Dict[str, Any]] = None
    ) -> None:
        """Capture LLM generation event in PostHog $ai_generation format."""
        if not self.is_enabled():
            return
            
        # Build standard PostHog $ai_generation event properties
        properties = {
            # Model and provider info
            "$ai_model": model,
            "$ai_provider": "openrouter",
            
            # Input and output content (full prompt/response tracking)
            "$ai_input": input_prompt,
            "$ai_output_choices": [{"message": {"content": output_content}}],
            
            # Performance metrics
            "$ai_response_time_ms": latency_ms,
            "$ai_timestamp": datetime.utcnow().isoformat(),
            
            # Token usage (estimated - OpenRouter doesn't always provide this)
            "$ai_input_tokens": len(input_prompt.split()) * 1.3,  # Rough estimate
            "$ai_output_tokens": len(output_content.split()) * 1.3,  # Rough estimate
            
            # Cost estimation (rough - would need model-specific pricing)
            "$ai_cost_usd": (len(input_prompt) + len(output_content)) * 0.000001,  # Very rough estimate
            
            # Correlation IDs for pipeline tracing
            "pipeline_step": pipeline_step,
            "indexing_run_id": indexing_run_id,
            
            # Generation ID for tracking
            "generation_id": str(uuid.uuid4()),
        }
        
        # Add any additional properties
        if additional_properties:
            properties.update(additional_properties)
        
        distinct_id = user_id or f"backend-{hash(sys.argv[0])}"
        
        try:
            self._client.capture(
                distinct_id=distinct_id,
                event="$ai_generation",
                properties=properties
            )
        except Exception:
            # Silently fail - don't let analytics break the pipeline
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