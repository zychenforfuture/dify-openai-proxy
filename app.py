#!/usr/bin/env python3
"""
Dify to OpenAI API Proxy - Clean version
Converts OpenAI API requests to Dify API calls
"""

import os
import json
import logging
from flask import Flask, request, jsonify
import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
DIFY_API_BASE = os.environ.get('DIFY_API_BASE', 'https://api.dify.ai/v1')

@app.route('/v1/chat/completions', methods=['POST'])
def chat_completions():
    try:
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return jsonify({"error": {"message": "Missing Authorization header", "type": "invalid_request_error", "code": 401}}), 401
        
        dify_api_key = auth_header.replace('Bearer ', '').strip()
        if not dify_api_key:
            return jsonify({"error": {"message": "API key required", "type": "invalid_request_error", "code": 401}}), 401
        
        openai_request = request.get_json()
        messages = openai_request.get('messages', [])
        stream = openai_request.get('stream', False)
        
        user_messages = [msg['content'] for msg in messages if msg['role'] == 'user']
        query = user_messages[-1] if user_messages else ""
        
        # Use exact same format as successful curl
        dify_request = {
            "inputs": {},
            "query": query,
            "response_mode": "streaming" if stream else "blocking",
            "conversation_id": "",
            "user": "abc-123"
        }
        
        headers = {
            'Authorization': f'Bearer {dify_api_key}',
            'Content-Type': 'application/json'
        }
        
        dify_url = f"{DIFY_API_BASE}/chat-messages"
        logger.info(f"Sending request to: {dify_url}")
        
        resp = requests.post(dify_url, json=dify_request, headers=headers)
        logger.info(f"Dify response status: {resp.status_code}")
        
        if resp.status_code != 200:
            logger.error(f"Dify error response: {resp.text}")
            return jsonify({
                "error": {
                    "message": f"Dify API error: {resp.status_code} - {resp.text}",
                    "type": "dify_api_error",
                    "code": resp.status_code
                }
            }), resp.status_code
        
        dify_response = resp.json()
        openai_response = {
            "id": dify_response.get("message_id", "dify-msg-unknown"),
            "object": "chat.completion",
            "created": dify_response.get("created_at", 0),
            "model": "dify-app",
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": dify_response.get("answer", "")
                },
                "finish_reason": "stop"
            }],
            "usage": {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0
            }
        }
        
        return jsonify(openai_response)
        
    except Exception as e:
        logger.error(f"Error: {e}")
        return jsonify({"error": {"message": str(e), "type": "proxy_error", "code": 500}}), 500

@app.route('/v1/models', methods=['GET'])
def list_models():
    return jsonify({
        "object": "list",
        "data": [{"id": "dify-app", "object": "model", "created": 1677649969, "owned_by": "dify"}]
    })

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy", "proxy": "dify-openai"})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port, debug=False)