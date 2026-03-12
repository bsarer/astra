#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REACT_PID=""

cleanup() {
    echo "[Astra] Cleaning up..."
    if [ -n "$REACT_PID" ]; then
        kill "$REACT_PID" 2>/dev/null || true
    fi
    docker stop astra-agent 2>/dev/null || true
}
trap cleanup EXIT

echo "[Astra] Starting Docker container (backend on port 7101)..."

# Stop and remove existing container
docker stop astra-agent 2>/dev/null || true
docker rm astra-agent 2>/dev/null || true

# Start container — backend on 7101, React dev server will be on 7100
docker run -d \
    --name astra-agent \
    --security-opt no-new-privileges \
    --cap-drop=ALL \
    -p 7101:8000 \
    -v "$SCRIPT_DIR/../../data:/app/data:ro" \
    --env-file "$SCRIPT_DIR/../.env" \
    astra-agent

echo "[Astra] Waiting for backend health check..."
for i in {1..30}; do
    if curl -s http://localhost:7101/health > /dev/null 2>&1; then
        echo "[Astra] Backend is healthy!"
        break
    fi
    sleep 1
done

echo "[Astra] Starting React dev server on port 7100..."
cd "$SCRIPT_DIR"
npm run dev &
REACT_PID=$!

echo "[Astra] Waiting for React dev server..."
for i in {1..30}; do
    if curl -s http://localhost:7100 > /dev/null 2>&1; then
        echo "[Astra] React dev server is ready!"
        break
    fi
    sleep 1
done

echo "[Astra] Starting Tauri..."
cargo tauri dev

# cleanup runs via trap
