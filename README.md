# Dify to OpenAI API Proxy

This proxy converts OpenAI API requests to Dify API calls, allowing you to use any OpenAI-compatible client with your Dify applications.

## Features
- ✅ OpenAI `/v1/chat/completions` endpoint compatibility
- ✅ Streaming and non-streaming responses
- ✅ Per-request Dify API key (via Authorization header)
- ✅ Multi-turn conversation support
- ✅ Docker container ready
- ✅ Health check endpoint

## Usage

### 1. Build and Run
```bash
docker-compose up -d
```

> Make sure `.env` defines `DIFY_API_BASE` (default `https://www.nas.bestfuture.top/v1`) and any other overrides before bringing the stack up; `docker-compose` loads these via `env_file`.

### 2. Make API Calls
Use your Dify API key as the Bearer token:

```bash
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_DIFY_API_KEY" \
  -d '{
    "model": "dify-app",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'
```

### 3. Integration with OpenAI Clients
Configure your OpenAI client to use:
- **Base URL**: `http://localhost:8000/v1`
- **API Key**: Your Dify API Key

## Environment Variables
- `DIFY_API_BASE` - Dify API base URL (default: `https://www.nas.bestfuture.top/v1`, configurable via `.env` and loaded by `docker-compose` via `env_file`).
- `PORT` - Server port (default: `8000`)

No need to set `DIFY_API_KEY` in environment - it's passed per request!

## Endpoints
- `POST /v1/chat/completions` - Chat completion endpoint
- `GET /v1/models` - List available models
- `GET /health` - Health check