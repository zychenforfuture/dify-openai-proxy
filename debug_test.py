#!/usr/bin/env python3
"""
Debug script to test Dify API call directly
"""

import requests
import json

# Your actual API key and endpoint
API_KEY = "app-4iYnZbELM04TXhHLaq0rmjPT"
BASE_URL = "https://www.nas.bestfuture.top/v1"

# Test request body (same as your successful curl)
test_request = {
    "inputs": {},
    "query": "你是谁",
    "response_mode": "blocking",
    "conversation_id": "",
    "user": "abc-123"
}

headers = {
    'Authorization': f'Bearer {API_KEY}',
    'Content-Type': 'application/json'
}

print("Testing direct Dify API call...")
print(f"URL: {BASE_URL}/chat-messages")
print(f"Headers: {headers}")
print(f"Request body: {json.dumps(test_request, indent=2)}")

try:
    response = requests.post(f"{BASE_URL}/chat-messages", json=test_request, headers=headers)
    print(f"Status code: {response.status_code}")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Error: {e}")