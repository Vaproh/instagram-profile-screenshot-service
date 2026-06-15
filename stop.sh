#!/bin/bash

SESSION_NAME="ig-profile"

if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
    echo "Stopping tmux session '$SESSION_NAME'..."
    tmux kill-session -t "$SESSION_NAME"
else
    echo "No active session found."
fi