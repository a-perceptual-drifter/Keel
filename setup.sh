#!/usr/bin/env bash
# Keel setup script
# Usage: bash setup.sh
# Safe to re-run. Skips steps already completed.

set -e

echo "=== Keel setup ==="

# 1. Python version check
if ! python3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)"; then
    echo "ERROR: Python 3.11+ required. Install from https://python.org"
    exit 1
fi

# 2. Virtual environment
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate

# 3. Install dependencies
echo "Installing Python dependencies..."
pip install --quiet --upgrade pip
pip install -e ".[dev]" --quiet

# 4. Ollama check / install (Linux only; other platforms get instructions)
if ! command -v ollama &> /dev/null; then
    if [ "$(uname -s)" = "Linux" ]; then
        echo "Installing Ollama..."
        curl -fsSL https://ollama.com/install.sh | sh || echo "WARN: Ollama install failed; continuing."
    else
        echo "NOTE: install Ollama from https://ollama.com and re-run."
    fi
fi

# 5. Pull required models (skip if already present / ollama unavailable)
if command -v ollama &> /dev/null; then
    echo "Pulling Ollama models (this may take a few minutes on first run)..."
    ollama pull llama3.2 2>/dev/null || true
    ollama pull nomic-embed-text 2>/dev/null || true
fi

# 6. Create default config if not present
mkdir -p config store logs
if [ ! -f "config/config.yaml" ]; then
    echo "Creating default config..."
    cp config/config.yaml.example config/config.yaml
fi
if [ ! -f "config/sources.yaml" ] && [ -f "config/sources.yaml.example" ]; then
    cp config/sources.yaml.example config/sources.yaml
fi
if [ ! -f "config/preferences.yaml" ] && [ -f "config/preferences.yaml.example" ]; then
    cp config/preferences.yaml.example config/preferences.yaml
fi

echo ""
echo "=== Setup complete ==="
echo ""
echo "Next: run 'keel --init' to set up your identity model"
echo "Then: run 'keel --schedule' to start the background agent"
echo "Then: run 'keel --chat' to open the conversation interface"
echo ""
echo "Or run 'keel --dev --chat' to try without Ollama using mock components"
