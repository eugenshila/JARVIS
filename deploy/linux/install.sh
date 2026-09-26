#!/bin/bash
# JARVIS Linux/macOS Quick Installer

set -e

echo "=== JARVIS Installer (Linux/macOS) ==="
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "ERROR: python3 not found. Install Python 3.10+"
    echo "Ubuntu/Debian: sudo apt install python3.11 python3.11-venv python3-pip"
    echo "macOS: brew install python@3.11"
    exit 1
fi

echo "Python: $(python3 --version)"

# Check if in JARVIS dir
if [ ! -f "pyproject.toml" ]; then
    echo "Cloning JARVIS..."
    if command -v git &> /dev/null; then
        git clone https://github.com/eugenshila/JARVIS
        cd JARVIS
    else
        echo "Git not found, downloading ZIP..."
        curl -L https://github.com/eugenshila/JARVIS/archive/main.zip -o jarvis.zip
        unzip jarvis.zip
        cd JARVIS-main
    fi
fi

# Venv
if [ ! -d ".venv" ]; then
    echo "Creating venv..."
    python3 -m venv .venv
fi

echo "Activating venv and installing..."
source .venv/bin/activate
pip install --upgrade pip
pip install -e .[all]

echo ""
echo "Running doctor..."
python -m jarvis.cli.main doctor

echo ""
echo "=== Install complete ==="
echo "Activate with: source .venv/bin/activate"
echo "Try: jarvis ask 'hello' --mock"
echo "For local AI: curl -fsSL https://ollama.com/install.sh | sh && ollama pull llama3.2:3b"
echo "Then: jarvis chat --engine ollama"
