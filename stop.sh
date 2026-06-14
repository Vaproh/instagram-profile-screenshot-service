#!/usr/bin/env bash
SESSION="ig-screenshot"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log()  { echo -e "${GREEN}[+]${NC} $1"; }
warn() { echo -e "${YELLOW}[!]${NC} $1"; }

# ── Kill specific windows we created ──
if tmux has-session -t "$SESSION" 2>/dev/null; then
    # Kill only our windows, not the whole session
    tmux kill-window -t "$SESSION:api" 2>/dev/null || true
    tmux kill-window -t "$SESSION:camofox" 2>/dev/null || true

    # If session has no windows left, kill it
    WINDOW_COUNT=$(tmux list-windows -t "$SESSION" 2>/dev/null | wc -l)
    if [ "$WINDOW_COUNT" -eq 0 ]; then
        tmux kill-session -t "$SESSION" 2>/dev/null || true
    fi
fi

log "Service stopped"