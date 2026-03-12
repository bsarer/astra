#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
COMPOSE_DIR="$SCRIPT_DIR/.."
REACT_PID=""

cleanup() {
    echo "[Astra] Cleaning up..."
    if [ -n "$REACT_PID" ]; then
        kill "$REACT_PID" 2>/dev/null || true
    fi
    docker compose -f "$COMPOSE_DIR/docker-compose.yml" down 2>/dev/null || true
}
trap cleanup EXIT

# Verify Qdrant is reachable (expected: agentic-qdrant on port 6333)
echo "[Astra] Checking Qdrant on port 6333..."
if curl -s http://localhost:6333/healthz > /dev/null 2>&1; then
    echo "[Astra] Qdrant is up."
else
    echo "[Astra] WARNING: Qdrant not reachable on port 6333 — memory will use in-process fallback."
fi

echo "[Astra] Starting backend via docker-compose..."
docker compose -f "$COMPOSE_DIR/docker-compose.yml" --env-file "$COMPOSE_DIR/.env" up -d --build

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
