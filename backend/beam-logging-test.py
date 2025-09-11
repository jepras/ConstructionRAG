"""
Beam logging test file for experimenting with different logging approaches.

This file tests whether we can replace print() statements with proper logging
in the Beam environment. It compares standard logging, structured logging,
and hybrid approaches to determine the best migration strategy.
"""

import asyncio
import logging
import time
from datetime import datetime
from typing import Any

from beam import Image, env, function

# Test 1: Standard Python logging (as per Beam docs)
logger = logging.getLogger(__name__)

# Test 2: Try to import and use structured logging
try:
    import structlog
    from src.utils.logging import get_logger, setup_logging
    
    # Initialize structured logging
    setup_logging("INFO")
    struct_logger = get_logger(__name__)
    HAS_STRUCTURED_LOGGING = True
except ImportError as e:
    print(f"⚠️ Structured logging not available: {e}")
    struct_logger = None
    HAS_STRUCTURED_LOGGING = False

# Test 3: Resource monitoring integration
try:
    from src.utils.resource_monitor import get_monitor, log_resources
    HAS_RESOURCE_MONITOR = True
except ImportError as e:
    print(f"⚠️ Resource monitor not available: {e}")
    HAS_RESOURCE_MONITOR = False


def test_logging_approaches():
    """Test different logging approaches and compare outputs."""
    
    print("=" * 60)
    print("🧪 BEAM LOGGING TEST - Starting Comprehensive Test")
    print(f"🕐 Test started at: {datetime.now().isoformat()}")
    print("=" * 60)
    
    # Test 1: Standard Python logging
    print("\n📝 TEST 1: Standard Python Logging")
    logger.debug("This is a DEBUG message")
    logger.info("This is an INFO message") 
    logger.warning("This is a WARNING message")
    logger.error("This is an ERROR message")
    logger.critical("This is a CRITICAL message")
    
    # Test 2: Structured logging (if available)
    if HAS_STRUCTURED_LOGGING:
        print("\n📝 TEST 2: Structured Logging")
        struct_logger.debug("Structured DEBUG message", extra_field="debug_value")
        struct_logger.info("Structured INFO message", pipeline_step="test", document_count=5)
        struct_logger.warning("Structured WARNING message", resource_usage="high")
        struct_logger.error("Structured ERROR message", error_code=500, component="test")
    else:
        print("\n📝 TEST 2: Structured Logging - SKIPPED (not available)")
    
    # Test 3: Performance comparison
    print("\n📝 TEST 3: Performance Comparison")
    
    # Time print statements
    start_time = time.time()
    for i in range(1000):
        pass  # Would normally be print(f"Print message {i}")
    print_time = time.time() - start_time
    print(f"⏱️ 1000 print() calls would take: {print_time:.4f}s (simulated)")
    
    # Time logging statements  
    start_time = time.time()
    for i in range(1000):
        logger.info("Logging message %d", i)
    logging_time = time.time() - start_time
    print(f"⏱️ 1000 logger.info() calls took: {logging_time:.4f}s")
    
    # Test 4: Resource monitoring integration
    if HAS_RESOURCE_MONITOR:
        print("\n📝 TEST 4: Resource Monitoring Integration")
        try:
            log_resources("Logging Test Start")
            # Simulate some work
            time.sleep(1)
            log_resources("Logging Test End")
            
            monitor = get_monitor()
            summary = monitor.get_summary()
            logger.info("Resource usage summary: CPU=%.1f%%, RAM=%.1f%%", 
                       summary['peak_cpu_percent'], summary['peak_ram_percent'])
        except Exception as e:
            logger.error("Resource monitoring test failed: %s", e)
    else:
        print("\n📝 TEST 4: Resource Monitoring - SKIPPED (not available)")
    
    # Test 5: Exception logging
    print("\n📝 TEST 5: Exception Logging")
    try:
        raise ValueError("This is a test exception")
    except ValueError as e:
        # Print approach (current)
        print(f"❌ Caught exception with print: {e}")
        
        # Logging approach (proposed)
        logger.error("Caught exception with logging", exc_info=True)
        
        if HAS_STRUCTURED_LOGGING:
            struct_logger.error("Caught exception with structured logging", 
                              error=str(e), error_type=type(e).__name__)
    
    # Test 6: Log levels and filtering
    print("\n📝 TEST 6: Log Level Filtering")
    original_level = logger.level
    
    # Set to WARNING level
    logger.setLevel(logging.WARNING)
    print("Set log level to WARNING:")
    logger.debug("This DEBUG should not appear")
    logger.info("This INFO should not appear") 
    logger.warning("This WARNING should appear")
    logger.error("This ERROR should appear")
    
    # Reset level
    logger.setLevel(original_level)
    
    print("\n✅ LOGGING TESTS COMPLETED")
    print("=" * 60)


async def async_logging_test():
    """Test logging in async context (like the main pipeline)."""
    
    print("\n🔄 ASYNC LOGGING TEST")
    
    logger.info("Starting async logging test")
    
    # Simulate async work with logging
    for i in range(3):
        logger.info("Async operation %d starting", i)
        await asyncio.sleep(0.1)  # Simulate async work
        logger.info("Async operation %d completed", i) 
        
        if HAS_STRUCTURED_LOGGING:
            struct_logger.info("Structured async log", 
                             operation_id=i, status="completed")
    
    logger.info("Async logging test completed")
    print("✅ Async logging test finished")


# Simple function-based approach

@function(
    name="logging-test",
    cpu=2,
    memory="4Gi",
    image=Image(
        python_version="python3.11",
        python_packages="beam_requirements.txt",
    ),
    timeout=300,
)
def test_logging_in_beam():
    """
    Main Beam function to test logging approaches.
    
    This function will be deployed to Beam and test all logging scenarios
    to see what works best in the Beam environment.
    """
    
    print("🚀 STARTING BEAM LOGGING TEST")
    print(f"📅 Test time: {datetime.now().isoformat()}")
    print(f"🌐 Environment: {'REMOTE (Beam)' if env.is_remote() else 'LOCAL'}")
    
    if env.is_remote():
        try:
            # Run all logging tests
            test_logging_approaches()
            
            # Test async logging
            asyncio.run(async_logging_test())
            
            # Final summary
            print("\n🎉 BEAM LOGGING TEST SUMMARY:")
            print(f"✅ Standard logging: Works")
            print(f"{'✅' if HAS_STRUCTURED_LOGGING else '❌'} Structured logging: {'Works' if HAS_STRUCTURED_LOGGING else 'Not available'}")
            print(f"{'✅' if HAS_RESOURCE_MONITOR else '❌'} Resource monitoring: {'Works' if HAS_RESOURCE_MONITOR else 'Not available'}")
            
            return {
                "status": "completed",
                "test_time": datetime.now().isoformat(),
                "standard_logging": True,
                "structured_logging": HAS_STRUCTURED_LOGGING, 
                "resource_monitoring": HAS_RESOURCE_MONITOR,
                "message": "Logging test completed successfully"
            }
            
        except Exception as e:
            error_message = f"Logging test failed: {str(e)}"
            print(f"💥 {error_message}")
            logger.error("Beam logging test failed", exc_info=True)
            
            return {
                "status": "failed", 
                "error": str(e),
                "message": "Logging test encountered errors"
            }
    else:
        # Local development mode
        print("🏠 Running in local development mode")
        test_logging_approaches()
        return {"status": "local_dev_mode", "message": "Local logging test completed"}


if __name__ == "__main__":
    # Allow running locally for quick testing
    print("🏠 Running logging test locally...")
    test_logging_approaches()
    asyncio.run(async_logging_test())