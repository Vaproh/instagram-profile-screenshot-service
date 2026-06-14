#!/usr/bin/env bash
SESSION="ig-screenshot"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log()  { echo -e "${GREEN}[+]${NC} $1"; }
warn() { echo -e "${YELLOW}[!]${NC} $1"; }

# ── Stop tmux session ──
if tmux has-session -t "$SESSION" 2>/dev/null; then
    log "Stopping tmux session '$SESSION'..."

    # Kill all processes in the session
    tmux kill-session -t "$SESSION" 2>/dev/null

    # Also kill any lingering Camofox processes on port 9377
    if lsof -ti:9377 &>/dev/null; then
        warn "Killing Camofox process on port 9377..."
        kill -9 $(lsof -ti:9377) 2>/dev/null || true
    fi

    log "Service stopped"
else
    warn "No tmux session '$SESSION' found. Nothing to stop."
fi

# Kill any remaining uvicorn processes for this project
if pgrep -f "uvicorn main:app" &>/dev/null; then
    warn "Killing remaining uvicorn processes..."
    pkill -f "uvicorn main:app" 2>/dev/null || true
fi
