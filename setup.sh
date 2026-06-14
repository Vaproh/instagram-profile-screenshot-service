#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

log()  { echo -e "${GREEN}[+]${NC} $1"; }
warn() { echo -e "${YELLOW}[!]${NC} $1"; }

# ── Python venv ──
if [ ! -d "$VENV_DIR" ]; then
    log "Creating Python virtual environment..."
    python3 -m venv "$VENV_DIR"
else
    log "Virtual environment exists"
fi

source "$VENV_DIR/bin/activate"

# ── Pip dependencies ──
log "Installing dependencies..."
pip install --quiet --upgrade pip
pip install --quiet -r "$SCRIPT_DIR/requirements.txt"
log "Pip packages installed"

# ── Docker ──
if ! command -v docker &> /dev/null; then
    warn "Docker not found. Please install Docker first."
fi

# ── Camofox Docker ──
if docker ps -a --format '{{.Names}}' | grep -q "^camofox$"; then
    log "Camofox Docker container already exists"
else
    log "Pulling Camofox Docker image..."
    docker pull nowsecure/camofox:latest
    log "Camofox image pulled"
fi

# ── Data directories ──
mkdir -p "$SCRIPT_DIR/data"
mkdir -p "$SCRIPT_DIR/data/logs"

# ── Config check ──
if [ ! -f "$SCRIPT_DIR/.env" ]; then
    warn ".env not found — copying from .env.example"
    cp "$SCRIPT_DIR/.env.example" "$SCRIPT_DIR/.env"
fi

log "Setup complete. Run ./start.sh to start the service."
