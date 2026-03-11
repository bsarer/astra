#!/bin/bash
set -e

echo "[Astra] Starting Docker container..."

# Load .env file
if [ -f "../.env" ]; then
    export $(cat ../.env | grep -v '^#' | xargs)
fi

# Stop and remove existing container
docker stop astra-agent 2>/dev/null || true
docker rm astra-agent 2>/dev/null || true

# Start container with all env vars
docker run -d \
    --name astra-agent \
    --security-opt no-new-privileges \
    --cap-drop=ALL \
    -p 7100:8000 \
    -v "$(pwd)/../../data:/app/data:ro" \
    --env-file "../.env" \
    astra-agent

echo "[Astra] Waiting for health check..."
for i in {1..30}; do
    if curl -s http://localhost:7100/health > /dev/null 2>&1; then
        echo "[Astra] Container is healthy!"
        break
    fi
    sleep 1
done

echo "[Astra] Starting Tauri..."
cargo tauri dev
