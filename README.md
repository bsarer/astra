# Astra OS

AI-powered desktop environment with generative UI. Users chat with an agent that can execute Python code, install packages, and render interactive widgets — all inside a sandboxed Docker container.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Tauri Desktop Shell                   │
│              (Rust — manages Docker lifecycle)           │
│                                                         │
│  ┌───────────────────────────────────────────────────┐  │
│  │              WebView (loads from container)        │  │
│  │                                                   │  │
│  │  ┌─────────────────┐   ┌───────────────────────┐  │  │
│  │  │   Chat Panel     │   │   Widget Canvas       │  │  │
│  │  │                 │   │   (GridStack)          │  │  │
│  │  │  user messages  │   │                       │  │  │
│  │  │  streamed tokens│   │  ┌───────┐ ┌───────┐  │  │  │
│  │  │                 │   │  │Widget │ │Widget │  │  │  │
│  │  │                 │   │  │(iframe)│ │(iframe)│  │  │  │
│  │  │                 │   │  └───────┘ └───────┘  │  │  │
│  │  └────────┬────────┘   └───────────────────────┘  │  │
│  │           │                                       │  │
│  │           │ WebSocket (ws://localhost:8000/ws)     │  │
│  └───────────┼───────────────────────────────────────┘  │
│              │                                          │
└──────────────┼──────────────────────────────────────────┘
               │
┌──────────────┼──────────────────────────────────────────┐
│  Docker      │                                          │
│  Container   ▼                                          │
│  ┌────────────────────────────────────────────────────┐ │
│  │           FastAPI Server (port 8000)                │ │
│  │                                                    │ │
│  │  /ws          — WebSocket (chat + widget events)   │ │
│  │  /health      — Health check                       │ │
│  │  /            — Static files (browser fallback)    │ │
│  │                                                    │ │
│  │  ┌──────────────────────────────────────────────┐  │ │
│  │  │          LangGraph Agent                     │  │ │
│  │  │                                              │  │ │
│  │  │  Tools:                                      │  │ │
│  │  │   • run_python_code  (30s timeout)           │  │ │
│  │  │   • render_widget    (HTML/CSS/JS → client)  │  │ │
│  │  │   • install_python_packages                  │  │ │
│  │  │                                              │  │ │
│  │  │  Memory: per-session via MemorySaver         │  │ │
│  │  └──────────────────────────────────────────────┘  │ │
│  └────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

### Components

- **Tauri Shell** (Rust) — Starts/stops the Docker container, polls `/health`, loads the frontend in a native window. Graceful shutdown on close.
- **FastAPI Backend** (Python) — WebSocket server with session management. Streams tokens and widget payloads to the client.
- **LangGraph Agent** — State machine with tool-calling loop. Executes code, renders widgets, installs packages.
- **Frontend** (HTML/JS) — Glassmorphic dark UI with split layout. Chat panel + GridStack widget canvas. Widgets render in sandboxed iframes.
- **Docker** — Python 3.12-slim, non-root user, `--no-new-privileges`, `--cap-drop=ALL`. All code execution is isolated.

### Message Protocol (WebSocket)

| Direction | Type | Purpose |
|-----------|------|---------|
| Server → Client | `token` | Streamed text chunk |
| Server → Client | `widget` | HTML/CSS/JS widget payload |
| Server → Client | `done` | Stream complete |
| Server → Client | `error` | Error message |
| Server → Client | `session_init` | Session ID assignment |
| Client → Server | `user_message` | User chat input |
| Client → Server | `widget_event` | Widget interaction callback |

## Getting Started

### Prerequisites

- Python 3.12+
- Docker (for containerized mode)
- Rust + Cargo (for Tauri desktop app)
- An OpenAI-compatible API key

### Option 1: Quick Start (local Python)

```bash
cd PoC/astra-poc-vc
bash run.sh
```

This will:
1. Prompt for your API key/model/base URL (creates `.env`)
2. Create a virtual environment
3. Install dependencies
4. Start the server on `http://localhost:8000`

Open `http://localhost:8000` in your browser.

### Option 2: Docker

```bash
cd PoC/astra-poc-vc
cp .env.example .env
# Edit .env with your credentials
docker-compose up --build
```

Server runs at `http://localhost:8000`.

### Option 3: Tauri Desktop App

```bash
cd PoC/astra-poc-vc/tauri-app
cargo tauri dev
```

Tauri will automatically start the Docker container, wait for it to be healthy, and load the UI in a native window.

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | Your API key (required) | — |
| `OPENAI_MODEL` | Model name | `gpt-5.3-codex` |
| `OPENAI_BASE_URL` | API base URL | `https://api.openai.com/v1` |

## Project Structure

```
PoC/astra-poc-vc/
├── main.py              # FastAPI server (WebSocket + health + static)
├── agent.py             # LangGraph agent with tools
├── session.py           # Session manager (session_id → thread_id)
├── models.py            # Typed message protocol (Pydantic)
├── prompts/             # System + tool prompts
├── static/              # Frontend (index.html + app.js)
├── Dockerfile           # Container image
├── docker-compose.yml   # Docker orchestration
├── run.sh               # Quick-start script
├── requirements.txt     # Python dependencies
└── tauri-app/           # Tauri desktop shell
    ├── astra.toml       # Tauri-Docker config
    └── src-tauri/       # Rust source
```

## License

See [LICENSE](LICENSE).
