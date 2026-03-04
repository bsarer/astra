#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

VENV_DIR=".venv"

# Create .env if it doesn't exist
if [ ! -f ".env" ]; then
    echo "========================================="
    echo "  Environment configuration"
    echo "========================================="
    echo ""

    read -rp "🌐 Enter base URL [https://api.openai.com/v1]: " BASE_URL
    BASE_URL="${BASE_URL:-https://api.openai.com/v1}"

    read -rp "🤖 Enter model name [gpt-5.3-codex]: " MODEL
    MODEL="${MODEL:-gpt-5.3-codex}"

    while true; do
        read -rp "🔑 Enter your OpenAI API Key (required): " API_KEY
        if [ -n "$API_KEY" ]; then
            break
        fi
        echo "   ❌ API Key is required. Please try again."
    done

    cat > .env << EOF
OPENAI_API_KEY="$API_KEY"
OPENAI_MODEL="$MODEL"
OPENAI_BASE_URL="$BASE_URL"
EOF
    echo ""
    echo "✅ .env file created successfully."
fi

# Create venv if it doesn't exist
if [ ! -d "$VENV_DIR" ]; then
    echo "🔧 Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
fi

# Activate venv
source "$VENV_DIR/bin/activate"

# Install dependencies
echo "📦 Installing dependencies..."
pip install -q -r requirements.txt

# Start the application
echo "🚀 Starting application..."
python main.py
