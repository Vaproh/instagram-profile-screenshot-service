#!/usr/bin/env bash
SESSION="ig-screenshot"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log()  { echo -e "${GREEN}[+]${NC} $1"; }
warn() { echo -e "${YELLOW}[!]${NC} $1"; }

# ── Stop tmux session ──
if tmux has-session -t "$SESSION" 2>/dev/null; then
    log "Stopping tmux session '$SESSION'..."
    tmux kill-session -t "$SESSION" 2>/dev/null
fi

# ── Kill remaining processes ──
if pgrep -f "uvicorn main:app" &>/dev/null; then
    warn "Killing remaining uvicorn processes..."
    pkill -f "uvicorn main:app" 2>/dev/null || true
fi

log "Service stopped"
