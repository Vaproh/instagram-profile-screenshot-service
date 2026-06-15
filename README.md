# Instagram Profile Card Service

Generates aesthetic profile cards for Instagram users using FastAPI + curl_cffi.

## Setup

```bash
./setup.sh
```

## Start/Stop

```bash
./start.sh      # Starts in tmux session 'ig-profile'
./stop.sh       # Stops the tmux session
```

## Configuration

Edit `.env` file:

```env
PORT=8080
PROXY_ENABLED=true
PROXY_SERVER=gw.dataimpulse.com
PROXY_PORT=823
PROXY_USERNAME=your_username
PROXY_PASSWORD=your_password
```

## API

### Health Check
```bash
curl http://localhost:8080/health
```

### Generate Profile Card
```bash
curl http://localhost:8080/profile/username -o card.png
```

## Requirements

- Python 3.10+
- curl-cffi
- Pillow
- FastAPI