#!/usr/bin/env python3
"""Test complete authenticated flow with RLS and access levels."""

import asyncio
import os
from pathlib import Path
from typing import Any

import httpx

BASE_URL = "http://localhost:8000"

class AuthFlowTester:
    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=60)
        self.access_token = None
        self.user_data = None
        self.project_id = None

    async def step1_login(self) -> dict[str, Any]:
        """Step 1: Login and store token."""
        print("🔐 Step 1: Login")
        
        response = await self.client.post(
            f"{self.base_url}/api/auth/signin",
            json={"email": "developerjeppe@outlook.com", "password": "test123"}
        )
        
        print(f"Status: {response.status_code}")
        data = response.json()
        
        if response.status_code == 200 and data.get("access_token"):
            self.access_token = data["access_token"]
            print(f"✅ Login successful, token: {self.access_token[:20]}...")
        else:
            print(f"❌ Login failed: {data}")
            return {}
            
        return data

    async def step2_create_project(self) -> dict[str, Any]:
        """Step 2: Create a project."""
        print("\n📁 Step 2: Create Project")
        
        if not self.access_token:
            print("❌ No access token")
            return {}
            
        headers = {"Authorization": f"Bearer {self.access_token}"}
        payload = {
            "name": "Test Project RLS",
            "description": "Testing RLS and access levels",
            "access_level": "owner"
        }
        
        response = await self.client.post(
            f"{self.base_url}/api/projects",
            json=payload,
            headers=headers
        )
        
        print(f"Status: {response.status_code}")
        data = response.json()
        print(f"Response: {data}")
        
        if response.status_code == 200 and data.get("id"):
            self.project_id = data["id"]
            print(f"✅ Project created with ID: {self.project_id}")
        else:
            print(f"❌ Project creation failed")
            
        return data

    async def step3_upload_document(self) -> dict[str, Any]:
        """Step 3: Upload document to project."""
        print("\n📄 Step 3: Upload Document to Project")
        
        if not self.access_token or not self.project_id:
            print("❌ Missing access token or project ID")
            return {}

        # Read the test PDF file
        pdf_path = "/Users/jepperasmussen/workspace/github.com/jepras/ConstructionRAG/data/external/construction_pdfs/smallest-doc.pdf"
        if not os.path.exists(pdf_path):
            print(f"❌ Test PDF not found at: {pdf_path}")
            return {}

        headers = {"Authorization": f"Bearer {self.access_token}"}
        
        # Prepare multipart form data
        with open(pdf_path, "rb") as f:
            files = {"files": ("smallest-doc.pdf", f, "application/pdf")}
            data = {"project_id": self.project_id}
            
            response = await self.client.post(
                f"{self.base_url}/api/uploads",
                files=files,
                data=data,
                headers=headers
            )
        
        print(f"Status: {response.status_code}")
        response_data = response.json()
        print(f"Response: {response_data}")
        
        if response.status_code == 200:
            print(f"✅ Document upload successful")
        else:
            print(f"❌ Document upload failed")
            
        return response_data

    async def debug_rls_issue(self):
        """Debug RLS issue by checking database state."""
        print("\n🔍 Debug: Checking RLS and JWT context")
        
        if not self.access_token:
            print("❌ No access token to debug")
            return
            
        # Check JWT payload
        import base64
        import json
        
        try:
            parts = self.access_token.split(".")
            if len(parts) == 3:
                payload = json.loads(base64.urlsafe_b64decode(parts[1] + "=="))
                print(f"JWT payload sub (user_id): {payload.get('sub')}")
                print(f"JWT payload aud: {payload.get('aud')}")
                print(f"JWT issued by: {payload.get('iss')}")
        except Exception as e:
            print(f"❌ Failed to decode JWT: {e}")

        # Test direct database query simulation
        if self.project_id:
            print(f"Expected project query: SELECT * FROM projects WHERE id = '{self.project_id}' AND user_id = '{payload.get('sub')}'")

    async def step4_list_projects(self) -> dict[str, Any]:
        """Step 4: List projects to verify access."""
        print("\n📋 Step 4: List Projects")
        
        if not self.access_token:
            print("❌ No access token")
            return {}
            
        headers = {"Authorization": f"Bearer {self.access_token}"}
        
        response = await self.client.get(
            f"{self.base_url}/api/projects",
            headers=headers
        )
        
        print(f"Status: {response.status_code}")
        data = response.json()
        print(f"Response: {data}")
        
        return data

    async def run_test(self):
        """Run complete test flow."""
        print("🚀 Starting authenticated flow test")
        print("="*50)
        
        try:
            # Step 1: Login
            await self.step1_login()
            
            if not self.access_token:
                return
            
            # Step 2: Create project
            await self.step2_create_project()
            
            # Step 4: List projects (verify creation)
            await self.step4_list_projects()
            
            # Debug RLS issue
            await self.debug_rls_issue()
            
            if not self.project_id:
                return
            
            # Step 3: Upload document
            await self.step3_upload_document()
            
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
        finally:
            await self.client.aclose()

async def main():
    """Main test function."""
    tester = AuthFlowTester()
    await tester.run_test()

if __name__ == "__main__":
    asyncio.run(main())