#!/bin/bash
set -e

echo ""
echo "[*] Instagram Profile Card Service - Setup"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1,2)
REQUIRED_VERSION="3.10"

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
    echo "[!] Python 3.10+ required. Found: $PYTHON_VERSION"
    exit 1
fi
echo "[+] Python version: $PYTHON_VERSION ✓"

# Create virtual environment
if [ ! -d "venv" ] && [ ! -d ".venv" ]; then
    echo "[*] Creating virtual environment..."
    python3 -m venv .venv
    echo "[+] Virtual environment created ✓"
else
    echo "[+] Virtual environment exists ✓"
fi

# Activate virtual environment
echo "[*] Activating virtual environment..."
source .venv/bin/activate

# Install dependencies
echo "[*] Installing dependencies..."
pip install -r requirements.txt --quiet
echo "[+] Dependencies installed ✓"

# Create .env from example if not exists
if [ ! -f .env ]; then
    if [ -f .env.example ]; then
        cp .env.example .env
        echo "[+] Created .env from .env.example"
        echo "[!] Please edit .env with your configuration"
    fi
else
    echo "[+] .env file exists ✓"
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "[+] Setup complete!"
echo ""
echo "  Next steps:"
echo "    1. Edit .env with your proxy credentials"
echo "    2. Run ./start.sh to start the service"
echo ""
echo "  Commands:"
echo "    ./start.sh   - Start service"
echo "    ./stop.sh    - Stop service"
echo "    ./setup.sh   - Re-run setup"
echo ""