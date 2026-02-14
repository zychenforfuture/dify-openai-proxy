import os
import logging
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, Request, HTTPException, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import httpx
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment variables
DIFY_API_KEY = os.getenv("DIFY_API_KEY")
DIFY_ENDPOINT = os.getenv("DIFY_ENDPOINT", "https://www.nas.bestfuture.top/v1/chat-messages")
DIFY_APP_ID = os.getenv("DIFY_APP_ID")  # Optional, can be passed in request

if not DIFY_API_KEY:
    logger.error("DIFY_API_KEY environment variable is required")
    raise ValueError("DIFY_API_KEY environment variable is required")

app = FastAPI(
    title="OpenAI-to-Dify API Proxy",
    description="Proxy that converts OpenAI API requests to Dify format",
    version="1.0.0"
)

# OpenAI request models
class Message(BaseModel):
    role: str
    content: str

class OpenAIChatCompletionRequest(BaseModel):
    model: str = Field(..., description="Model name (mapped to Dify app)")
    messages: List[Message]
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = None
    stream: Optional[bool] = False
    user: Optional[str] = None

# Dify request models
class DifyChatMessageRequest(BaseModel):
    inputs: Dict[str, Any] = Field(default_factory=dict)
    query: str
    response_mode: str = "blocking"  # "blocking" or "streaming"
    user: str = "openai-proxy-user"
    conversation_id: Optional[str] = None

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "dify_endpoint": DIFY_ENDPOINT}

@app.post("/v1/chat/completions")
async def chat_completions(request: OpenAIChatCompletionRequest, raw_request: Request):
    """
    OpenAI-compatible chat completions endpoint
    Converts OpenAI requests to Dify format and proxies the response
    """
    try:
        logger.info(f"Received OpenAI request for model: {request.model}")
        
        # Extract the last user message (Dify typically expects a single query)
        # We'll use the last message as the main query
        if not request.messages:
            raise HTTPException(status_code=400, detail="No messages provided")
        
        # Find the last user message
        last_user_message = None
        for msg in reversed(request.messages):
            if msg.role == "user":
                last_user_message = msg.content
                break
        
        if last_user_message is None:
            raise HTTPException(status_code=400, detail="No user message found")
        
        # Build Dify request
        dify_request = DifyChatMessageRequest(
            query=last_user_message,
            user=request.user or "openai-proxy-user",
            response_mode="blocking"  # Start with non-streaming
        )
        
        # Add conversation context if available (first message as system prompt)
        if len(request.messages) > 1:
            system_messages = [msg.content for msg in request.messages if msg.role == "system"]
            if system_messages:
                dify_request.inputs["system_prompt"] = "\n".join(system_messages)
        
        logger.info(f"Forwarding to Dify endpoint: {DIFY_ENDPOINT}")
        
        # Make request to Dify
        async with httpx.AsyncClient(timeout=30.0) as client:
            headers = {
                "Authorization": f"Bearer {DIFY_API_KEY}",
                "Content-Type": "application/json"
            }
            
            # Use custom app ID if provided in model name or env var
            app_id = DIFY_APP_ID or request.model
            
            dify_url = f"{DIFY_ENDPOINT}/{app_id}"
            
            response = await client.post(
                dify_url,
                json=dify_request.dict(exclude_none=True),
                headers=headers
            )
            
            logger.info(f"Dify response status: {response.status_code}")
            
            if response.status_code != 200:
                logger.error(f"Dify error: {response.text}")
                # Try to parse Dify error response
                try:
                    error_data = response.json()
                    error_msg = error_data.get("message", response.text)
                except:
                    error_msg = response.text
                
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Dify API error: {error_msg}"
                )
            
            dify_response = response.json()
            
            # Convert Dify response back to OpenAI format
            openai_response = convert_dify_to_openai(dify_response, request.model)
            
            return JSONResponse(content=openai_response)
            
    except httpx.RequestError as e:
        logger.error(f"HTTP request error: {str(e)}")
        raise HTTPException(status_code=502, detail=f"Upstream request failed: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

def convert_dify_to_openai(dify_response: Dict[str, Any], model: str) -> Dict[str, Any]:
    """
    Convert Dify response format to OpenAI-compatible format
    """
    try:
        # Dify blocking response structure
        answer = dify_response.get("answer", "")
        conversation_id = dify_response.get("conversation_id", "")
        
        openai_response = {
            "id": f"chatcmpl-{conversation_id[:16] if conversation_id else 'proxy'}",
            "object": "chat.completion",
            "created": dify_response.get("created_at", 0),
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": answer
                    },
                    "finish_reason": "stop"
                }
            ],
            "usage": {
                "prompt_tokens": dify_response.get("metadata", {}).get("tokens", {}).get("prompt_tokens", 0),
                "completion_tokens": dify_response.get("metadata", {}).get("tokens", {}).get("completion_tokens", len(answer.split())),
                "total_tokens": dify_response.get("metadata", {}).get("tokens", {}).get("total_tokens", len(answer.split()) + 10)
            }
        }
        
        return openai_response
        
    except Exception as e:
        logger.error(f"Error converting Dify response: {str(e)}")
        # Fallback response
        return {
            "id": "chatcmpl-fallback",
            "object": "chat.completion",
            "created": 0,
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": dify_response.get("answer", "Error processing response")
                    },
                    "finish_reason": "stop"
                }
            ],
            "usage": {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0
            }
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)