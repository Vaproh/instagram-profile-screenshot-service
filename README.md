# Instagram Profile Screenshot Service

A lightweight FastAPI backend that captures cropped screenshots of Instagram profiles using the Camofox browser engine.

## Features

- **Screenshot capture** via Camofox anti-detect browser
- **Profile header cropping** (PFP, username, stats, bio)
- **Rate limiting** to prevent abuse
- **Request ID tracking** for debugging and tracing
- **Structured logging** with process time metrics
- **Health checks** (liveness + readiness probes)
- **Graceful shutdown** handling
- **Retry logic** for transient failures
- **Input validation** for Instagram usernames

## How It Works

```
Client Request
    │
    ▼
POST /tabs → Create Camofox tab
    │
    ▼
POST /tabs/{id}/navigate → Go to instagram.com/{username}
    │
    ▼
sleep 5s → Wait for page to render
    │
    ▼
GET /tabs/{id}/snapshot → Check page content
    │
    ├─ If "profile isn't available" → Return 404
    │
    ├─ If button "Close" [e1] → Click to dismiss login overlay
    │       │
    │       ▼
    │   sleep 2s → Wait for animation
    │
    ▼
GET /tabs/{id}/screenshot → Capture raw PNG
    │
    ▼
Crop to profile header (PIL)
    │
    ▼
DELETE /tabs/{id} → Cleanup
    │
    ▼
Return cropped PNG to client
```

## Prerequisites

- Python 3.10+
- Camofox browser running at `http://localhost:9377`

## Setup

```bash
# Enter project directory
cd ig-screenshot

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env if needed
```

## Running

```bash
# Activate virtual environment
source .venv/bin/activate

# Start server
uvicorn main:app --host 0.0.0.0 --port 8080

# Or run directly
python main.py
```

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `CAMOFOX_URL` | `http://localhost:9377` | Camofox browser REST API URL |
| `CAMOFOX_USER_ID` | `ig-screenshot-service` | User ID label for Camofox sessions |
| `CAMOFOX_TIMEOUT` | `15.0` | Request timeout in seconds |
| `CAMOFOX_CONNECT_TIMEOUT` | `2.0` | Connection timeout in seconds |
| `PAGE_LOAD_WAIT` | `3.0` | Seconds to wait after navigation |
| `OVERLAY_DISMISS_WAIT` | `1.0` | Seconds to wait after clicking overlay |
| `LOG_LEVEL` | `INFO` | Logging level |
| `RATE_LIMIT_PER_MINUTE` | `30` | Rate limit per IP |
| `HOST` | `0.0.0.0` | Server host |
| `PORT` | `8080` | Server port |
| `CROP_LEFT` | `610` | Left crop coordinate (for 1280x720) |
| `CROP_TOP` | `65` | Top crop coordinate |
| `CROP_RIGHT` | `1210` | Right crop coordinate |
| `CROP_BOTTOM` | `270` | Bottom crop coordinate |

## API Endpoints

### Health Checks

#### `GET /health`

Combined health status.

```json
{
  "status": "ok",
  "camofox": true
}
```

#### `GET /health/live`

Liveness probe — always returns 200 if service is running.

```json
{"status": "ok"}
```

#### `GET /health/ready`

Readiness probe — returns 503 if Camofox is unavailable.

```json
{
  "status": "ok",
  "camofox": true
}
```

### Screenshot

#### `GET /screenshot/{username}`

Capture a screenshot of an Instagram profile (cropped or raw).

**Parameters:**
- `username` (path): Instagram username (1-30 characters, alphanumeric with `.` `_`)
- `crop` (query, optional): Whether to crop to profile header (default: `true`). Set to `false` for full-page screenshot.

**Responses:**

| Status | Description | Body |
|--------|-------------|------|
| 200 | Success | PNG image (cropped or raw depending on `crop` param) |
| 400 | Invalid username | `{"detail": "Invalid username"}` |
| 404 | Profile unavailable/deactivated | `{"detail": "profile isn't available"}` |
| 429 | Rate limit exceeded | `{"error": "Rate limit exceeded"}` |
| 503 | Camofox not running | `{"detail": "Camofox browser not available"}` |
| 504 | Page load timeout | `{"detail": "Page load timeout"}` |

**Headers in response:**
- `X-Request-ID`: Unique request identifier for tracing
- `X-Process-Time`: Request processing time (e.g., `3.421s`)

## Testing

```bash
# Health check
curl http://localhost:8080/health

# Liveness probe
curl http://localhost:8080/health/live

# Readiness probe
curl http://localhost:8080/health/ready

# Screenshot an active profile (cropped, default)
curl -o test.png http://localhost:8080/screenshot/akiraa.init

# Screenshot with raw full page (no crop)
curl -o test_raw.png "http://localhost:8080/screenshot/akiraa.init?crop=false"

# Test deactivated profile (returns 404)
curl http://localhost:8080/screenshot/1lazyxan

# With request ID tracing
curl -H "X-Request-ID: my-test-123" http://localhost:8080/health
```

## Project Structure

```
ig-screenshot/
├── main.py          # FastAPI app, routes, middleware
├── camofox.py       # Camofox REST API client with retries
├── cropper.py       # PIL-based image cropping
├── config.py        # Pydantic settings configuration
├── requirements.txt # Python dependencies
├── .env.example     # Configuration template
└── README.md        # This file
```

## Production Deployment

### Docker

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
```

### Systemd Service

```ini
[Unit]
Description=Instagram Screenshot Service
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/ig-screenshot
ExecStart=/opt/ig-screenshot/.venv/bin/uvicorn main:app --host 0.0.0.0 --port 8080
Restart=always

[Install]
WantedBy=multi-user.target
```

### Reverse Proxy (nginx)

```nginx
server {
    listen 443 ssl;
    server_name screenshots.example.com;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Request-ID $request_id;
    }
}
```

## Error Handling

- **Camofox connection error**: Returns 503 — service gracefully handles when Camofox is not running
- **Navigation timeout (15s)**: Returns 504 with retry logic for transient failures
- **Profile deactivated**: Returns 404 — detected via accessibility snapshot before screenshot
- **Rate limiting**: Returns 429 — configurable per-IP limits
- **Tab cleanup**: Always executed via context manager, even on errors
- **Concurrent requests**: Each request gets its own isolated tab

## Monitoring

The service exposes several metrics useful for monitoring:

1. **Health endpoints** for Kubernetes probes
2. **X-Request-ID** header for request tracing
3. **X-Process-Time** header for latency monitoring
4. **Structured JSON logs** for log aggregation

Example log entry:
```
2026-06-14 19:30:00 - main - INFO - abc-123 | GET /screenshot/akiraa.init | 200 | 3.421s
```
