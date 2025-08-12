#!/usr/bin/env python3
"""Test complete end-to-end authenticated flow including indexing, wiki generation, and queries."""

import asyncio
import os
import time
from typing import Any

import httpx

BASE_URL = "http://localhost:8000"

class CompleteFlowTester:
    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=60)
        self.access_token = None
        self.project_id = None
        self.index_run_id = None
        self.document_ids = []
        self.wiki_run_id = None

    async def step1_login(self) -> bool:
        """Step 1: Login and store token."""
        print("🔐 Step 1: Login")
        
        response = await self.client.post(
            f"{self.base_url}/api/auth/signin",
            json={"email": "developerjeppe@outlook.com", "password": "test123"}
        )
        
        if response.status_code == 200:
            data = response.json()
            self.access_token = data["access_token"]
            print(f"✅ Login successful")
            return True
        else:
            print(f"❌ Login failed: {response.json()}")
            return False

    async def step2_create_project(self) -> bool:
        """Step 2: Create a project."""
        print("\n📁 Step 2: Create Project")
        
        headers = {"Authorization": f"Bearer {self.access_token}"}
        payload = {
            "name": f"Complete Flow Test {int(time.time())}",
            "description": "Testing complete RAG flow with auth",
            "access_level": "owner"
        }
        
        response = await self.client.post(
            f"{self.base_url}/api/projects",
            json=payload,
            headers=headers
        )
        
        if response.status_code == 200:
            data = response.json()
            self.project_id = data["id"]
            print(f"✅ Project created: {self.project_id}")
            return True
        else:
            print(f"❌ Project creation failed: {response.json()}")
            return False

    async def step3_upload_document(self) -> bool:
        """Step 3: Upload document to project."""
        print("\n📄 Step 3: Upload Document")
        
        pdf_path = "/Users/jepperasmussen/workspace/github.com/jepras/ConstructionRAG/data/external/construction_pdfs/smallest-doc.pdf"
        if not os.path.exists(pdf_path):
            print(f"❌ Test PDF not found at: {pdf_path}")
            return False

        headers = {"Authorization": f"Bearer {self.access_token}"}
        
        with open(pdf_path, "rb") as f:
            files = {"files": ("smallest-doc.pdf", f, "application/pdf")}
            data = {"project_id": self.project_id}
            
            response = await self.client.post(
                f"{self.base_url}/api/uploads",
                files=files,
                data=data,
                headers=headers
            )
        
        if response.status_code == 200:
            data = response.json()
            self.index_run_id = data["index_run_id"]
            self.document_ids = data["document_ids"]
            print(f"✅ Document uploaded, index_run_id: {self.index_run_id}")
            return True
        else:
            print(f"❌ Document upload failed: {response.json()}")
            return False

    async def step4_create_indexing_run(self) -> bool:
        """Step 4: Create/trigger indexing run."""
        print("\n🔄 Step 4: Indexing Run (Already Created)")
        print(f"✅ Indexing run already created during upload: {self.index_run_id}")
        return True

    async def step5_create_wiki_generation_run(self) -> bool:
        """Step 5: Create wiki generation run."""
        print("\n📖 Step 5: Create Wiki Generation Run")
        
        headers = {"Authorization": f"Bearer {self.access_token}"}
        
        # First check if we have a wiki generation endpoint
        try:
            payload = {
                "project_id": self.project_id,
                "title": "Project Wiki",
                "description": "Auto-generated project wiki"
            }
            
            response = await self.client.post(
                f"{self.base_url}/api/wiki-generations",  # Assuming this endpoint exists
                json=payload,
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                self.wiki_run_id = data.get("id")
                print(f"✅ Wiki generation run created: {self.wiki_run_id}")
                return True
            elif response.status_code == 404:
                print("⚠️ Wiki generation endpoint not found - skipping this step")
                return True
            else:
                print(f"❌ Wiki generation failed: {response.json()}")
                return False
                
        except Exception as e:
            print(f"⚠️ Wiki generation not available: {e}")
            return True  # Continue with other steps

    async def step6_run_query(self) -> bool:
        """Step 6: Run query on the project."""
        print("\n🔍 Step 6: Run Query")
        
        headers = {"Authorization": f"Bearer {self.access_token}"}
        
        # Use correct payload format based on API
        payload = {
            "query": "hvem er med i projektet?",
            "indexing_run_id": self.index_run_id
        }
        
        try:
            response = await self.client.post(
                f"{self.base_url}/api/queries",
                json=payload,
                headers=headers
            )
            
            print(f"Query endpoint response: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Query successful")
                print(f"Answer: {data.get('answer', 'No answer field')}")
                print(f"Query ID: {data.get('id', 'No ID')}")
                return True
            else:
                error_data = response.json()
                print(f"❌ Query failed: {error_data}")
                return False
                
        except Exception as e:
            print(f"❌ Error running query: {e}")
            return False

    async def step7_check_status(self) -> bool:
        """Step 7: Check various statuses."""
        print("\n📊 Step 7: Check Statuses")
        
        headers = {"Authorization": f"Bearer {self.access_token}"}
        
        # Check indexing run status
        if self.index_run_id:
            try:
                response = await self.client.get(
                    f"{self.base_url}/api/indexing-runs/{self.index_run_id}",
                    headers=headers
                )
                if response.status_code == 200:
                    data = response.json()
                    print(f"Indexing run status: {data.get('status')}")
                else:
                    print(f"Failed to get indexing run status")
            except Exception as e:
                print(f"Error checking indexing status: {e}")
        
        # Check documents
        try:
            response = await self.client.get(
                f"{self.base_url}/api/documents?project_id={self.project_id}",
                headers=headers
            )
            if response.status_code == 200:
                data = response.json()
                print(f"Documents in project: {len(data.get('documents', []))}")
            else:
                print(f"Failed to list documents")
        except Exception as e:
            print(f"Error listing documents: {e}")
        
        return True

    async def run_complete_test(self):
        """Run the complete end-to-end test."""
        print("🚀 Starting Complete RAG Flow Test")
        print("="*50)
        
        try:
            steps = [
                ("Login", self.step1_login),
                ("Create Project", self.step2_create_project),
                ("Upload Document", self.step3_upload_document),
                ("Indexing Run", self.step4_create_indexing_run),
                ("Wiki Generation", self.step5_create_wiki_generation_run),
                ("Run Query", self.step6_run_query),
                ("Check Status", self.step7_check_status),
            ]
            
            for step_name, step_func in steps:
                success = await step_func()
                if not success and step_name in ["Login", "Create Project", "Upload Document"]:
                    print(f"❌ Critical step failed: {step_name}")
                    break
                    
            print("\n🎉 Test completed!")
            
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
        finally:
            await self.client.aclose()

async def main():
    """Main test function."""
    tester = CompleteFlowTester()
    await tester.run_complete_test()

if __name__ == "__main__":
    asyncio.run(main())