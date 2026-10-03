#!/usr/bin/env python3
"""
Test script for the Todo backend API.

This script demonstrates testing the Todo backend using httpx>=0.26.0
with FastAPI>=0.109.0.
"""

import httpx
import json
import asyncio
from pathlib import Path
import sys

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def test_backend_api():
    """Test the backend API with httpx"""
    base_url = "http://localhost:8000"
    
    print("=== Testing Todo Backend API ===\n")
    
    # Test health check if available
    try:
        with httpx.Client(timeout=10.0) as client:
            print("1. Testing health check endpoint...")
            response = client.get(f"{base_url}/api/chat/health")
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                print(f"   Response: {response.json()}")
            print()
    except httpx.ConnectError:
        print("[ERROR] Cannot connect to backend. Make sure it's running on http://localhost:8000")
        return False
    except Exception as e:
        print(f"[WARNING] Health check failed: {str(e)}\n")

    # Test chat endpoint
    print("2. Testing chat endpoint...")
    try:
        with httpx.Client(timeout=10.0) as client:
            payload = {
                "message": "Hello, can you help me with my tasks?"
            }
            response = client.post(f"{base_url}/api/chat/", json=payload)
            print(f"   Status: {response.status_code}")
            print(f"   Response: {response.json()}")
            print()
    except Exception as e:
        print(f"[ERROR] Chat endpoint failed: {str(e)}\n")

    print("=== Test completed ===")
    return True


async def test_backend_api_async():
    """Test the backend API asynchronously"""
    base_url = "http://localhost:8000"
    
    print("=== Testing Todo Backend API (Async) ===\n")
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            print("1. Testing async chat endpoint...")
            payload = {
                "message": "Test async message"
            }
            response = await client.post(f"{base_url}/api/chat/", json=payload)
            print(f"   Status: {response.status_code}")
            print(f"   Response: {response.json()}")
            print()
    except httpx.ConnectError:
        print("[ERROR] Cannot connect to backend. Make sure it's running.")
        return False
    except Exception as e:
        print(f"[ERROR] Async test failed: {str(e)}\n")
    
    print("=== Async test completed ===")
    return True


if __name__ == "__main__":
    print("Starting Todo Backend Tests\n")
    
    # Run synchronous tests
    test_backend_api()
    
    print("\n" + "="*50 + "\n")
    
    # Run async tests (optional)
    try:
        asyncio.run(test_backend_api_async())
    except Exception as e:
        print(f"Async tests not available: {str(e)}")