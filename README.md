# Instagram Profile Screenshot Service

Capture cropped screenshots of Instagram profiles via a FastAPI backend using Camofox anti-detect browser.

## Features

- Cropped profile header screenshots (PFP, username, stats, bio)
- Raw screenshot option (`?crop=false`)
- Auto-dismisses cookie consent and login overlays
- Detects deactivated/non-existent profiles → returns 404
- Rate limiting (30 req/min per IP)
- Health checks (liveness + readiness)
- Request ID tracking for debugging
- Structured logging

## Quick Start

```bash
# Clone
git clone https://github.com/Vaproh/instagram-profile-screenshot-service.git
cd instagram-profile-screenshot-service/ig-screenshot

# Setup
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env

# Run
uvicorn main:app --host 0.0.0.0 --port 8080
```

## API

### `GET /screenshot/{username}`

**Parameters:**
- `username` (path) - Instagram username
- `crop` (query, default: `true`) - `false` for raw 1280x720 screenshot

**Responses:**

| Status | Body |
|--------|------|
| 200 | PNG image |
| 400 | `{"detail": "Invalid username"}` - invalid format (special chars, too long) |
| 404 | `{"detail": "profile isn't available"}` - deactivated or non-existent |
| 429 | `{"error": "Rate limit exceeded"}` |
| 503 | `{"detail": "Camofox browser not available"}` |
| 504 | `{"detail": "Page load timeout"}` |

**Examples:**
```bash
# Cropped (default)
curl -o profile.png http://localhost:8080/screenshot/akiraa.init

# Raw full page
curl -o raw.png "http://localhost:8080/screenshot/akiraa.init?crop=false"
```

### `GET /health`

Returns combined health status with Camofox availability.

```bash
curl http://localhost:8080/health
# {"status": "ok", "camofox": true}
```

### `GET /health/live`

Liveness probe — returns 200 if service is running.

### `GET /health/ready`

Readiness probe — returns 503 if Camofox is unavailable.

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `CAMOFOX_URL` | `http://localhost:9377` | Camofox browser URL |
| `CAMOFOX_USER_ID` | `ig-screenshot-service` | Session label |
| `CAMOFOX_TIMEOUT` | `15.0` | Request timeout (s) |
| `PAGE_LOAD_WAIT` | `3.0` | Wait after navigate (s) |
| `OVERLAY_DISMISS_WAIT` | `1.0` | Wait after clicking overlay (s) |
| `RATE_LIMIT_PER_MINUTE` | `30` | Requests per IP per minute |
| `CROP_LEFT` | `610` | Crop left coordinate |
| `CROP_TOP` | `65` | Crop top coordinate |
| `CROP_RIGHT` | `1210` | Crop right coordinate |
| `CROP_BOTTOM` | `270` | Crop bottom coordinate |

## Edge Cases

| Case | Detection | Response |
|------|----------|----------|
| Deactivated profile | Snapshot: "Profile isn't available" | 404 |
| Non-existent profile | Snapshot: "This page isn't available" | 404 |
| Cookie consent popup | Auto-detected | Dismissed automatically |
| Login overlay | Auto-detected | Dismissed automatically |
| Camofox offline | Connection refused | 503 |
| Timeout | 15s exceeded | 504 |
| Rate limited | Per-IP limit | 429 |

**Overlay priority:** Close → Decline cookies → Accept cookies → Accept all

## Workflow

```
POST /tabs → Create tab
POST /tabs/{id}/navigate → Navigate to instagram.com/{username}
sleep 3s → Wait for page load
GET /tabs/{id}/snapshot → Check for overlays / errors
  └─ If cookie/login overlay → Click → sleep 1s → recheck
  └─ If unavailable → return 404
GET /tabs/{id}/screenshot → Capture PNG
DELETE /tabs/{id} → Cleanup tab
Return image to client
```

## Project Structure

```
ig-screenshot/
├── main.py          # FastAPI app, routes
├── camofox.py      # Browser client, overlay detection
├── cropper.py      # PIL image cropping
├── config.py       # Pydantic settings
├── requirements.txt
├── .env.example
└── README.md
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

### Systemd

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

### nginx

```nginx
location / {
    proxy_pass http://127.0.0.1:8080;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Request-ID $request_id;
}
```

## Requirements

- Python 3.10+
- Camofox browser at `http://localhost:9377`
