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

# Create Camofox window
tmux new-window -t "$SESSION" -n "camofox" "
    echo 'Starting Camofox browser via Docker...'
    docker run --rm --name camofox -p 9377:9377 nowsecure/camofox:latest 2>&1 | tee -a $CAMOFOX_LOG
"

sleep 1

if tmux has-session -t "$SESSION" 2>/dev/null; then
    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}  Service is running in tmux!${NC}"
    echo -e ""
    echo -e "  Session:  ${CYAN}$SESSION${NC}"
    echo -e "  API:      ${CYAN}http://localhost:8080${NC}"
    echo -e "  Health:   ${CYAN}http://localhost:8080/health${NC}"
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
