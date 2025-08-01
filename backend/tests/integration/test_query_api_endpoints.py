"""
Integration tests for FastAPI query endpoints.

This test suite verifies:
1. POST /api/query - Query processing endpoint
2. GET /api/query/history - Query history endpoint
3. POST /api/query/{id}/feedback - Feedback submission endpoint
4. GET /api/query/quality-dashboard - Quality dashboard endpoint
"""

import asyncio
import sys
import os
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

# Add the src directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from fastapi.testclient import TestClient
from src.main import app
from src.config.database import get_supabase_admin_client


class TestQueryAPIEndpoints:
    """Integration test suite for query API endpoints"""

    def __init__(self):
        self.client = TestClient(app)
        self.test_results = []

        # Test user credentials (you may need to adjust these)
        self.test_user = {"email": "test@example.com", "password": "testpassword123"}
        self.auth_token = None

    async def run_all_tests(self):
        """Run all API endpoint tests"""
        print("🚀 Starting Query API Endpoints Integration Tests...")
        print("=" * 80)

        # Setup: Get authentication token
        await self._setup_authentication()

        # Test cases
        test_cases = [
            {
                "name": "Process Construction Query",
                "method": "POST",
                "endpoint": "/api/query",
                "data": {"query": "Hvad er principperne for regnvandshåndtering?"},
            },
            {
                "name": "Get Query History",
                "method": "GET",
                "endpoint": "/api/query/history",
                "params": {"limit": 10, "offset": 0},
            },
            {
                "name": "Get Quality Dashboard",
                "method": "GET",
                "endpoint": "/api/query/quality-dashboard",
                "params": {"time_period": "7d"},
            },
        ]

        for i, test_case in enumerate(test_cases, 1):
            print(f"\n📝 Test Case {i}: {test_case['name']}")
            print(f"Endpoint: {test_case['method']} {test_case['endpoint']}")
            print("-" * 60)

            result = await self._run_single_test(test_case)
            self.test_results.append(result)

        # Test feedback submission (requires a query ID from previous tests)
        await self._test_feedback_submission()

        # Generate test report
        self._generate_test_report()

    async def _setup_authentication(self):
        """Setup authentication for tests"""
        try:
            # Try to authenticate with test user
            auth_response = self.client.post("/api/auth/login", json=self.test_user)

            if auth_response.status_code == 200:
                self.auth_token = auth_response.json().get("access_token")
                print("✅ Authentication successful")
            else:
                print("⚠️  Authentication failed, using mock token for testing")
                self.auth_token = "mock_token_for_testing"

        except Exception as e:
            print(f"⚠️  Authentication setup failed: {e}")
            self.auth_token = "mock_token_for_testing"

    async def _run_single_test(self, test_case: dict) -> dict:
        """Run a single API endpoint test"""
        start_time = asyncio.get_event_loop().time()

        try:
            # Prepare headers with authentication
            headers = (
                {"Authorization": f"Bearer {self.auth_token}"}
                if self.auth_token
                else {}
            )

            # Make request based on method
            if test_case["method"] == "POST":
                response = self.client.post(
                    test_case["endpoint"],
                    json=test_case.get("data", {}),
                    headers=headers,
                )
            elif test_case["method"] == "GET":
                response = self.client.get(
                    test_case["endpoint"],
                    params=test_case.get("params", {}),
                    headers=headers,
                )

            # Calculate test duration
            duration = (asyncio.get_event_loop().time() - start_time) * 1000

            # Analyze response
            success = response.status_code in [200, 201]
            response_data = response.json() if response.content else {}

            result = {
                "test_name": test_case["name"],
                "endpoint": f"{test_case['method']} {test_case['endpoint']}",
                "success": success,
                "status_code": response.status_code,
                "duration_ms": duration,
                "response_size": len(str(response_data)),
                "error": (
                    None if success else response_data.get("detail", "Unknown error")
                ),
            }

            if success:
                print(
                    f"✅ PASS - Status: {response.status_code}, Duration: {duration:.1f}ms"
                )
                print(f"   Response size: {result['response_size']} chars")
            else:
                print(f"❌ FAIL - Status: {response.status_code}")
                print(f"   Error: {result['error']}")

            return result

        except Exception as e:
            duration = (asyncio.get_event_loop().time() - start_time) * 1000
            result = {
                "test_name": test_case["name"],
                "endpoint": f"{test_case['method']} {test_case['endpoint']}",
                "success": False,
                "status_code": None,
                "duration_ms": duration,
                "response_size": 0,
                "error": str(e),
            }
            print(f"❌ ERROR - Exception: {e}")
            return result

    async def _test_feedback_submission(self):
        """Test feedback submission endpoint"""
        print(f"\n📝 Test Case: Submit Query Feedback")
        print(f"Endpoint: POST /api/query/{{id}}/feedback")
        print("-" * 60)

        try:
            # First, get a query from history to submit feedback on
            headers = (
                {"Authorization": f"Bearer {self.auth_token}"}
                if self.auth_token
                else {}
            )

            history_response = self.client.get(
                "/api/query/history", params={"limit": 1}, headers=headers
            )

            if history_response.status_code == 200:
                history_data = history_response.json()
                if history_data.get("queries"):
                    query_id = history_data["queries"][0]["id"]

                    # Submit feedback
                    feedback_data = {
                        "relevance_score": 4,
                        "helpfulness_score": 5,
                        "accuracy_score": 4,
                        "comments": "Very helpful response about rainwater handling",
                    }

                    feedback_response = self.client.post(
                        f"/api/query/{query_id}/feedback",
                        json=feedback_data,
                        headers=headers,
                    )

                    success = feedback_response.status_code == 200
                    response_data = (
                        feedback_response.json() if feedback_response.content else {}
                    )

                    result = {
                        "test_name": "Submit Query Feedback",
                        "endpoint": f"POST /api/query/{query_id}/feedback",
                        "success": success,
                        "status_code": feedback_response.status_code,
                        "duration_ms": 0,  # Not measured for this test
                        "response_size": len(str(response_data)),
                        "error": (
                            None
                            if success
                            else response_data.get("detail", "Unknown error")
                        ),
                    }

                    if success:
                        print(f"✅ PASS - Status: {feedback_response.status_code}")
                        print(f"   Feedback submitted successfully")
                    else:
                        print(f"❌ FAIL - Status: {feedback_response.status_code}")
                        print(f"   Error: {result['error']}")

                    self.test_results.append(result)
                else:
                    print("⚠️  No queries in history to test feedback submission")
            else:
                print(
                    f"⚠️  Could not get query history for feedback test: {history_response.status_code}"
                )

        except Exception as e:
            result = {
                "test_name": "Submit Query Feedback",
                "endpoint": "POST /api/query/{id}/feedback",
                "success": False,
                "status_code": None,
                "duration_ms": 0,
                "response_size": 0,
                "error": str(e),
            }
            print(f"❌ ERROR - Exception: {e}")
            self.test_results.append(result)

    def _generate_test_report(self):
        """Generate comprehensive test report"""
        print("\n" + "=" * 80)
        print("📊 QUERY API ENDPOINTS TEST REPORT")
        print("=" * 80)

        # Calculate statistics
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result["success"])
        failed_tests = total_tests - passed_tests
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0

        # Performance metrics
        durations = [
            result["duration_ms"]
            for result in self.test_results
            if result["duration_ms"] > 0
        ]
        avg_duration = sum(durations) / len(durations) if durations else 0
        max_duration = max(durations) if durations else 0

        print(f"\n📈 SUMMARY:")
        print(f"   Total Tests: {total_tests}")
        print(f"   Passed: {passed_tests} ✅")
        print(f"   Failed: {failed_tests} ❌")
        print(f"   Success Rate: {success_rate:.1f}%")
        print(f"   Average Duration: {avg_duration:.1f}ms")
        print(f"   Max Duration: {max_duration:.1f}ms")

        print(f"\n📋 DETAILED RESULTS:")
        for i, result in enumerate(self.test_results, 1):
            status = "✅ PASS" if result["success"] else "❌ FAIL"
            print(f"   {i}. {result['test_name']} - {status}")
            print(f"      Endpoint: {result['endpoint']}")
            print(f"      Status Code: {result['status_code']}")
            print(f"      Duration: {result['duration_ms']:.1f}ms")
            if result["error"]:
                print(f"      Error: {result['error']}")
            print()

        # Recommendations
        print(f"\n💡 RECOMMENDATIONS:")
        if success_rate == 100:
            print("   🎉 All tests passed! API endpoints are working correctly.")
        elif success_rate >= 80:
            print("   ⚠️  Most tests passed. Review failed tests for issues.")
        else:
            print("   🚨 Multiple test failures. Review API implementation.")

        if avg_duration > 5000:
            print("   ⏱️  Response times are slow. Consider performance optimization.")
        elif avg_duration > 2000:
            print("   ⏱️  Response times are acceptable but could be improved.")
        else:
            print("   ⚡ Response times are good!")

        print("\n" + "=" * 80)


async def main():
    """Main test runner"""
    tester = TestQueryAPIEndpoints()
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())
