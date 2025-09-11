# Beam Timeout Notification Implementation Guide

## Problem
Currently, when Beam tasks timeout (after 30 minutes), no notifications are sent to admin or users. The indexing_run status remains "pending" forever, and users never know their upload failed.

## Current Infrastructure
- ✅ Error notification system exists (`LoopsService.send_error_notification()` and `send_user_error_notification()`)
- ✅ Error webhook endpoint exists (`/api/wiki/internal/error-webhook`)
- ✅ Beam timeout is configured at 30 minutes (`beam-app.py:331`)
- ❌ Beam doesn't call error webhook on timeout/cancelled/expired

## Implementation Steps

### 1. Modify Beam Worker to Handle Timeouts
**File**: `backend/beam-app.py`

The Beam `@task_queue` decorator should handle timeout exceptions. Wrap the main function to catch timeout:

```python
# In process_documents() function
try:
    # Existing code...
    return asyncio.run(run_indexing_pipeline_on_beam(...))
except Exception as e:
    # Check if it's a timeout/cancellation
    error_type = "timeout" if "timeout" in str(e).lower() else "cancelled"
    
    # Call error webhook for timeout/cancellation
    asyncio.run(trigger_error_webhook(
        indexing_run_id, 
        f"Beam task {error_type}: {str(e)}",
        webhook_url,
        webhook_api_key
    ))
    
    # Re-raise to let Beam know it failed
    raise
```

### 2. Update Error Webhook to Handle Timeout Status
**File**: `backend/src/api/wiki.py`

In `handle_beam_error()`, check for timeout/cancelled keywords:

```python
# Detect if this is a timeout vs regular failure
if "timeout" in error_message.lower():
    error_stage = "beam_timeout"
elif "cancelled" in error_message.lower() or "expired" in error_message.lower():
    error_stage = "beam_cancelled"
else:
    error_stage = request.error_stage  # Use provided stage
```

### 3. Enhance Error Context for Timeouts
When storing error in database, include timeout-specific context:

```python
error_context = {
    "stage": error_stage,
    "step": "beam_processing",
    "error": error_message,
    "context": {
        "indexing_run_id": indexing_run_id,
        "user_email": user_email,
        "timeout_minutes": 30,  # Add timeout duration
        "timestamp": datetime.utcnow().isoformat()
    }
}
```

## Testing

### Manual Test
1. Create a test Beam task that sleeps for 31 minutes
2. Verify error webhook is called with timeout message
3. Check admin and user receive notifications

### Simulate Timeout
```bash
curl -X POST https://api.specfinder.io/api/wiki/internal/error-webhook \
  -H "Content-Type: application/json" \
  -H "X-API-Key: construction-rag-webhook-secret-2024" \
  -d '{
    "indexing_run_id": "test-timeout-run-123",
    "error_message": "Beam task timeout: Task exceeded 30 minute limit",
    "error_stage": "beam_timeout"
  }'
```

## Expected Behavior After Implementation

When Beam task times out:
1. ✅ Beam catches timeout exception
2. ✅ Calls error webhook with timeout message
3. ✅ Database updated: status='failed', error_message includes timeout
4. ✅ Admin gets technical notification about timeout
5. ✅ User gets friendly "something went wrong" email
6. ✅ No jobs stuck in "pending" forever

## Key Files to Modify
- `backend/beam-app.py` - Add timeout exception handling
- `backend/src/api/wiki.py` - Enhance error webhook for timeout detection (optional)

## Environment Variables
No new environment variables needed. Uses existing:
- `BEAM_WEBHOOK_API_KEY`
- `BACKEND_API_URL`
- `LOOPS_API_KEY`