#!/bin/bash
set -e

source .venv/bin/activate

if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

PORT=${PORT:-8080}
HOST=${HOST:-0.0.0.0}

if [ "$PROXY_ENABLED" = "true" ] && [ -n "$PROXY_SERVER" ]; then
    echo "Starting with proxy: $PROXY_SERVER"
fi

SESSION_NAME="ig-profile"

if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
    echo "Session $SESSION_NAME already exists. Killing..."
    tmux kill-session -t "$SESSION_NAME"
fi

echo "Starting Instagram Profile Card Service on $HOST:$PORT..."
tmux new-session -d -s "$SESSION_NAME" "uvicorn main:app --host $HOST --port $PORT --reload"
echo "Service running in tmux session '$SESSION_NAME'"