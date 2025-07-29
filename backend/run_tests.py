#!/usr/bin/env python3
"""
Test runner for the backend pipeline tests
"""

import os
import sys
import asyncio
from pathlib import Path

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))


def run_integration_tests():
    """Run all integration tests"""
    print("🧪 Running Integration Tests...")

    # Run partition step integration test
    print("\n📋 Testing Partition Step Integration...")
    try:
        from tests.integration.test_partition_step_integration import (
            test_partition_step_with_db,
        )

        success = asyncio.run(test_partition_step_with_db())
        if success:
            print("✅ Partition Step Integration Test: PASSED")
        else:
            print("❌ Partition Step Integration Test: FAILED")
            return False
    except Exception as e:
        print(f"❌ Partition Step Integration Test: ERROR - {e}")
        return False

    # Run auth integration test
    print("\n🔐 Testing Auth Integration...")
    try:
        from tests.integration.test_auth_integration import test_auth_integration

        success = asyncio.run(test_auth_integration())
        if success:
            print("✅ Auth Integration Test: PASSED")
        else:
            print("❌ Auth Integration Test: FAILED")
            return False
    except Exception as e:
        print(f"❌ Auth Integration Test: ERROR - {e}")
        return False

    return True


def run_unit_tests():
    """Run all unit tests"""
    print("🧪 Running Unit Tests...")
    # TODO: Add unit tests when we create them
    print("ℹ️  No unit tests yet")
    return True


if __name__ == "__main__":
    print("🚀 Starting Backend Pipeline Tests...")

    # Run integration tests
    integration_success = run_integration_tests()

    # Run unit tests
    unit_success = run_unit_tests()

    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Results Summary:")
    print(
        f"   Integration Tests: {'✅ PASSED' if integration_success else '❌ FAILED'}"
    )
    print(f"   Unit Tests: {'✅ PASSED' if unit_success else '❌ FAILED'}")

    if integration_success and unit_success:
        print("\n🎉 All tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed!")
        sys.exit(1)
