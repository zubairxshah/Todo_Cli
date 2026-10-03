#!/usr/bin/env python3
"""
Test script for chatbot task execution
"""

import httpx
import json
import uuid
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(".env.local"))

BACKEND_URL = "http://localhost:8000"
TEST_USER_ID = str(uuid.uuid4())

print("=" * 60)
print("Testing Chatbot Task Execution")
print("=" * 60)

# Test 1: Add a task
print("\n" + "=" * 60)
print("Test 1: Add a Task")
print("=" * 60)

test_message = "add a new task visit to park"

try:
    response = httpx.post(
        f"{BACKEND_URL}/api/chat/",
        json={"message": test_message, "user_id": TEST_USER_ID},
        timeout=30.0
    )
    chat_data = response.json()
    print(f"Command: {test_message}")
    print(f"Status: {chat_data.get('status')}")
    print(f"Response: {chat_data.get('message')}")
    print(f"Data: {chat_data.get('data')}")
except Exception as e:
    print(f"✗ Test failed: {e}")

# Test 2: List tasks
print("\n" + "=" * 60)
print("Test 2: List Tasks")
print("=" * 60)

test_message = "show all tasks"

try:
    response = httpx.post(
        f"{BACKEND_URL}/api/chat/",
        json={"message": test_message, "user_id": TEST_USER_ID},
        timeout=30.0
    )
    chat_data = response.json()
    print(f"Command: {test_message}")
    print(f"Status: {chat_data.get('status')}")
    print(f"Response: {chat_data.get('message')}")
except Exception as e:
    print(f"✗ Test failed: {e}")

# Test 3: Create another task
print("\n" + "=" * 60)
print("Test 3: Add Another Task")
print("=" * 60)

test_message = "create task buy groceries"

try:
    response = httpx.post(
        f"{BACKEND_URL}/api/chat/",
        json={"message": test_message, "user_id": TEST_USER_ID},
        timeout=30.0
    )
    chat_data = response.json()
    print(f"Command: {test_message}")
    print(f"Status: {chat_data.get('status')}")
    print(f"Response: {chat_data.get('message')}")
except Exception as e:
    print(f"✗ Test failed: {e}")

# Test 4: List tasks again
print("\n" + "=" * 60)
print("Test 4: List Tasks Again")
print("=" * 60)

test_message = "list all my tasks"

try:
    response = httpx.post(
        f"{BACKEND_URL}/api/chat/",
        json={"message": test_message, "user_id": TEST_USER_ID},
        timeout=30.0
    )
    chat_data = response.json()
    print(f"Command: {test_message}")
    print(f"Status: {chat_data.get('status')}")
    print(f"Response:\n{chat_data.get('message')}")
except Exception as e:
    print(f"✗ Test failed: {e}")

print("\n" + "=" * 60)
print("Task Execution Tests Complete")
print("=" * 60)
