#!/usr/bin/env bash
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"
SESSION="ig-screenshot"
LOG_DIR="$SCRIPT_DIR/data/logs"
API_LOG="$LOG_DIR/api.log"
CAMOFOX_LOG="$LOG_DIR/camofox.log"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
RED='\033[0;31m'
NC='\033[0m'

log()  { echo -e "${GREEN}[+]${NC} $1"; }
warn() { echo -e "${YELLOW}[!]${NC} $1"; }
err()  { echo -e "${RED}[x]${NC} $1"; }

# ── Pre-flight ──
if [ ! -d "$VENV_DIR" ]; then
    err "Virtual environment not found. Run ./setup.sh first."
    exit 1
fi

if [ ! -f "$SCRIPT_DIR/.camofox_dir" ]; then
    err "Camofox directory not set. Run ./setup.sh first."
    exit 1
fi

CAMOFOX_DIR=$(cat "$SCRIPT_DIR/.camofox_dir")

if [ ! -d "$CAMOFOX_DIR" ]; then
    err "Camofox directory not found: $CAMOFOX_DIR"
    exit 1
fi

mkdir -p "$LOG_DIR"

# ── Kill existing session ──
if tmux has-session -t "$SESSION" 2>/dev/null; then
    warn "Stopping existing session '$SESSION'..."
    tmux kill-session -t "$SESSION"
fi

# ── Start tmux session with two windows ──
log "Starting Camofox and API in tmux session '$SESSION'..."

# Create session with API window
tmux new-session -d -s "$SESSION" -n "api" "
    cd $SCRIPT_DIR
    source $VENV_DIR/bin/activate
    uvicorn main:app --host 0.0.0.0 --port 8080 2>&1 | tee -a $API_LOG
"

# Create Camofox window with proxy env vars if enabled
if [ -f "$SCRIPT_DIR/.env" ]; then
    source "$SCRIPT_DIR/.env"
fi

if [ "$PROXY_ENABLED" = "true" ] && [ -n "$PROXY_SERVER" ]; then
    log "Starting Camofox with proxy: $PROXY_SERVER"
    tmux new-window -t "$SESSION" -n "camofox" "
        cd $CAMOFOX_DIR
        PROXY_STRATEGY=backconnect \
        PROXY_BACKCONNECT_HOST=$PROXY_SERVER \
        PROXY_BACKCONNECT_PORT=823 \
        PROXY_USERNAME=$PROXY_USERNAME \
        PROXY_PASSWORD=$PROXY_PASSWORD \
        npm start 2>&1 | tee -a $CAMOFOX_LOG
    "
else
    log "Starting Camofox without proxy"
    tmux new-window -t "$SESSION" -n "camofox" "
        cd $CAMOFOX_DIR
        npm start 2>&1 | tee -a $CAMOFOX_LOG
    "
fi

sleep 1

if tmux has-session -t "$SESSION" 2>/dev/null; then
    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}  Service is running in tmux!${NC}"
    echo -e ""
    echo -e "  Session:  ${CYAN}$SESSION${NC}"
    echo -e "  API:      ${CYAN}http://localhost:8080${NC}"
    echo -e "  Health:   ${CYAN}http://localhost:8080/health${NC}"
    echo -e "  Screenshot: ${CYAN}http://localhost:8080/screenshot/{username}${NC}"
    echo -e ""
    echo -e "  Attach:   ${CYAN}tmux attach -t $SESSION${NC}"
    echo -e "  API log:  ${CYAN}$API_LOG${NC}"
    echo -e "  Camofox log: ${CYAN}$CAMOFOX_LOG${NC}"
    echo -e "  Stop:     ${CYAN}./stop.sh${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
else
    err "Failed to start tmux session."
    exit 1
fi
