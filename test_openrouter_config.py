#!/usr/bin/env python3
"""
Test script to verify OpenRouter configuration and chatbot functionality
"""

import httpx
import json
import os
from pathlib import Path

# Load environment from .env.local
from dotenv import load_dotenv
load_dotenv(Path(".env.local"))

BACKEND_URL = "http://localhost:8000"
OPEN_ROUTER_API_KEY = os.getenv("OPEN_ROUTER_API_KEY")
OPEN_ROUTER_URL = os.getenv("OPEN_ROUTER_URL")

print("=" * 60)
print("OpenRouter Configuration Check")
print("=" * 60)

# Check environment variables
print(f"\nOpenRouter API Key: {'✓ Configured' if OPEN_ROUTER_API_KEY else '✗ Not configured'}")
print(f"OpenRouter URL: {OPEN_ROUTER_URL}")

# Test 1: Health check
print("\n" + "=" * 60)
print("Test 1: Backend Health Check")
print("=" * 60)

try:
    response = httpx.get(f"{BACKEND_URL}/api/chat/health")
    health_data = response.json()
    print(f"✓ Health Status: {health_data.get('status')}")
    print(f"  Service: {health_data.get('service')}")
    print(f"  Version: {health_data.get('version', 'N/A')}")
except Exception as e:
    print(f"✗ Health check failed: {e}")
    exit(1)

# Test 2: Simple chat message
print("\n" + "=" * 60)
print("Test 2: Chat API - Simple Message")
print("=" * 60)

test_message = "Hello, can you help me manage my tasks?"

try:
    response = httpx.post(
        f"{BACKEND_URL}/api/chat/",
        json={"message": test_message},
        timeout=30.0
    )
    chat_data = response.json()
    print(f"Status: {chat_data.get('status')}")
    print(f"Response: {chat_data.get('message')[:150]}...")
    if chat_data.get('status') == 'success':
        print("✓ Chat API is working!")
    else:
        print(f"⚠ Response status: {chat_data.get('status')}")
except Exception as e:
    print(f"✗ Chat test failed: {e}")

# Test 3: Natural language task command
print("\n" + "=" * 60)
print("Test 3: Chat API - Task Command")
print("=" * 60)

task_command = "Update task 1: change the title to 'Buy groceries' and mark it as completed"

try:
    response = httpx.post(
        f"{BACKEND_URL}/api/chat/",
        json={"message": task_command},
        timeout=30.0
    )
    chat_data = response.json()
    print(f"Command: {task_command}")
    print(f"Response: {chat_data.get('message')[:200]}...")
    if chat_data.get('status') == 'success':
        print("✓ Task command processed!")
    else:
        print(f"⚠ Response status: {chat_data.get('status')}")
except Exception as e:
    print(f"✗ Task command test failed: {e}")

# Test 4: Summary
print("\n" + "=" * 60)
print("Configuration Summary")
print("=" * 60)

if OPEN_ROUTER_API_KEY:
    print("✓ OpenRouter API Key: Configured")
    print(f"  Key: {OPEN_ROUTER_API_KEY[:20]}...")
    print("✓ Real API responses will be used")
else:
    print("⚠ OpenRouter API Key: Not configured")
    print("✓ Simulated responses will be used")

print(f"✓ Backend: http://localhost:8000")
print(f"✓ Chat API: {BACKEND_URL}/api/chat/")
print("\n" + "=" * 60)
