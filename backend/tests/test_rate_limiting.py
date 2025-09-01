#!/usr/bin/env python3
"""Test script for rate limiting middleware."""

import sys
from pathlib import Path

# Add backend src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.middleware.rate_limiter import RateLimiter, RATE_LIMIT_ANONYMOUS, WHITELISTED_IPS


def test_rate_limiting():
    """Test the rate limiting functionality."""
    
    limiter = RateLimiter()
    
    print(f"Rate limit for anonymous users: {RATE_LIMIT_ANONYMOUS} PDFs per hour")
    print(f"Whitelisted IPs: {WHITELISTED_IPS}")
    print()
    
    # Test 1: Normal IP should be rate limited
    test_ip = "192.168.1.100"
    print(f"Testing rate limiting for IP: {test_ip}")
    
    # Should allow first 50 files
    for i in range(50):
        allowed, info = limiter.check_rate_limit(test_ip, file_count=1, is_authenticated=False)
        if not allowed:
            print(f"  ❌ Failed at file {i+1}")
            break
    else:
        print(f"  ✅ Allowed first 50 files")
    
    # 51st file should be blocked
    allowed, info = limiter.check_rate_limit(test_ip, file_count=1, is_authenticated=False)
    if not allowed:
        print(f"  ✅ Blocked 51st file (retry after {info['retry_after_seconds']} seconds)")
    else:
        print(f"  ❌ Should have blocked 51st file")
    
    print()
    
    # Test 2: Localhost should not be rate limited
    print("Testing localhost (should be whitelisted)...")
    limiter.reset_all()  # Clear limits
    
    for i in range(100):
        allowed, info = limiter.check_rate_limit("127.0.0.1", file_count=1, is_authenticated=False)
        if not allowed:
            print(f"  ❌ Localhost was rate limited at file {i+1}")
            break
    else:
        print(f"  ✅ Localhost allowed 100+ files (whitelisted)")
    
    print()
    
    # Test 3: Authenticated users should not be rate limited
    print("Testing authenticated user...")
    limiter.reset_all()  # Clear limits
    test_ip_auth = "192.168.1.200"
    
    for i in range(100):
        allowed, info = limiter.check_rate_limit(test_ip_auth, file_count=1, is_authenticated=True)
        if not allowed:
            print(f"  ❌ Authenticated user was rate limited at file {i+1}")
            break
    else:
        print(f"  ✅ Authenticated user allowed 100+ files")
    
    print()
    
    # Test 4: Batch upload counting
    print("Testing batch upload (10 files at once)...")
    limiter.reset_all()  # Clear limits
    test_ip_batch = "192.168.1.300"
    
    # Upload 40 files (should work)
    allowed, info = limiter.check_rate_limit(test_ip_batch, file_count=40, is_authenticated=False)
    print(f"  40 files: {'✅ Allowed' if allowed else '❌ Blocked'} (remaining: {info.get('remaining', 'N/A')})")
    
    # Try 11 more (should fail, would be 51 total)
    allowed, info = limiter.check_rate_limit(test_ip_batch, file_count=11, is_authenticated=False)
    print(f"  11 more files: {'✅ Allowed' if allowed else '❌ Blocked'} (would exceed limit)")
    
    # Try 10 more (should work, exactly 50)
    allowed, info = limiter.check_rate_limit(test_ip_batch, file_count=10, is_authenticated=False)
    print(f"  10 more files: {'✅ Allowed' if allowed else '❌ Blocked'} (exactly at limit)")
    
    print("\n✅ All rate limiting tests completed!")


if __name__ == "__main__":
    test_rate_limiting()