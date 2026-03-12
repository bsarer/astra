# Astra OS

AI-powered agentic desktop environment with declarative generative UI. Chat with an agent that reads emails, checks calendars, analyzes stocks, and renders interactive floating widgets — all inside a native Tauri window backed by a sandboxed Docker container.

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│                   Tauri Desktop Shell                    │
│             (Rust — manages Docker lifecycle)            │
│                                                          │
│  ┌────────────────────────────────────────────────────┐  │
│  │          React Frontend (Vite, port 7100)          │  │
│  │                                                    │  │
│  │  ┌──────────────────┐  ┌───────────────────────┐  │  │
│  │  │   Chat Panel      │  │   Desktop Canvas      │  │  │
│  │  │   (CopilotKit)    │  │   (Floating Windows)  │  │  │
│  │  │                  │  │                       │  │  │
│  │  │  AG-UI stream    │  │  ┌─────┐  ┌───────┐  │  │  │
│  │  │  events render   │  │  │Clock│  │Stocks │  │  │  │
│  │  │  via             │  │  └─────┘  └───────┘  │  │  │
│  │  │  useRenderTool   │  │  ┌──────────────┐    │  │  │
│  │  │  Call hook       │  │  │  Dashboard   │    │  │  │
│  │  │                  │  │  └──────────────┘    │  │  │
│  │  └──────────────────┘  └───────────────────────┘  │  │
│  │           │                                        │  │
│  │           │  HTTP POST /api/copilotkit             │  │
│  │           │  (Vite proxy → localhost:7101)          │  │
│  └───────────┼────────────────────────────────────────┘  │
└──────────────┼───────────────────────────────────────────┘
               │
┌──────────────┼───────────────────────────────────────────┐
│  Docker      │  Container (port 7101 → 8000 inside)     │
│              ▼                                           │
│  ┌─────────────────────────────────────────────────────┐ │
│  │          FastAPI + CopilotKit AG-UI Server          │ │
│  │                                                     │ │
│  │  POST /api/copilotkit  — AG-UI protocol stream      │ │
│  │  GET  /health          — Health check               │ │
│  │                                                     │ │
│  │  ┌───────────────────────────────────────────────┐  │ │
│  │  │           LangGraph Agent (gpt-4o)            │  │ │
│  │  │                                               │  │ │
│  │  │  Tools:                                       │  │ │
│  │  │   • emit_ui          (declarative A2UI)       │  │ │
│  │  │   • run_python_code  (sandboxed, 30s timeout) │  │ │
│  │  │   • install_python_packages                   │  │ │
│  │  │   • list_emails / get_email                   │  │ │
│  │  │   • list_calendar_events                      │  │ │
│  │  │   • get_stock_quote / analyze_stock_email     │  │ │
│  │  │   • get_upcoming_trip                         │  │ │
│  │  │                                               │  │ │
│  │  │  Canvas state tracking + email deduplication   │  │ │
│  │  │  Background email poller (30s interval)        │  │ │
│  │  └───────────────────────────────────────────────┘  │ │
│  └─────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────┘
```

### Key Concepts

- **AG-UI Protocol**: The backend streams events (tool calls, text deltas, run lifecycle) to the frontend via CopilotKit's AG-UI transport over HTTP POST.
- **Declarative UI (A2UI)**: The agent calls `emit_ui` with a flat component tree. The frontend's `useRenderToolCall` hook intercepts these and renders them as draggable, resizable floating windows on the desktop canvas.
- **Canvas Awareness**: The agent tracks what surfaces are already rendered and avoids duplicating widgets.
- **Email Poller**: Background task checks for new emails every 30s and triggers stock analysis if relevant.

## Getting Started

### Prerequisites

- Docker
- Node.js 18+ and npm
- Rust + Cargo (for Tauri desktop app)
- An OpenAI API key (or compatible provider)

### 1. Configure Environment

```bash
cp PoC/astra-poc-vc/.env.example PoC/astra-poc-vc/.env
```

Edit `PoC/astra-poc-vc/.env` — values must NOT have quotes:

```
OPENAI_API_KEY=sk-your-key-here
OPENAI_MODEL=gpt-4o
OPENAI_BASE_URL=https://api.openai.com/v1
DEBUG=0
DATA_PROVIDER=mock
MIKE_EMAIL=mike.astraos@zohomail.eu
MIKE_EMAIL_PASSWORD=your-app-password
MIKE_EMAIL_PROVIDER=zoho
```

Set `DATA_PROVIDER=mock` to use local JSON persona files (no real email/calendar connection needed). Set to `zoho` for live Zoho Mail integration.

### 2. Build Docker Image

```bash
docker build -t astra-agent PoC/astra-poc-vc/
```

Rebuild after any backend Python changes.

### 3. Install Frontend Dependencies

```bash
cd PoC/astra-poc-vc/tauri-app
npm install
```

### 4. Run (Recommended: start-dev.sh)

```bash
cd PoC/astra-poc-vc/tauri-app
./start-dev.sh
```

This script:
1. Stops any existing `astra-agent` container
2. Starts a new Docker container (backend on port 7101)
3. Mounts `data/` directory read-only for persona files
4. Starts the Vite React dev server on port 7100
5. Launches the Tauri desktop app

You can also open `http://localhost:7100` in a browser.

### 4b. Run Manually (if start-dev.sh doesn't suit you)

```bash
# Terminal 1 — Backend
docker stop astra-agent; docker rm astra-agent
docker run -d --name astra-agent \
  --security-opt no-new-privileges --cap-drop=ALL \
  -p 7101:8000 \
  -v "$(pwd)/../../data:/app/data:ro" \
  --env-file ../.env \
  astra-agent

# Terminal 2 — Frontend
cd PoC/astra-poc-vc/tauri-app
npm run dev

# Terminal 3 — Tauri (optional, for native window)
cd PoC/astra-poc-vc/tauri-app
cargo tauri dev
```

### Ports

| Port | Service |
|------|---------|
| 7100 | React/Vite dev server (frontend) |
| 7101 | Docker container (backend, mapped from 8000 inside) |

The Vite dev server proxies `/api/*` requests to `localhost:7101`.

## Project Structure

```
PoC/astra-poc-vc/
├── main.py                  # FastAPI server (AG-UI endpoint, email poller, health)
├── agent.py                 # LangGraph agent (tools, canvas tracking, prompts)
├── session.py               # Session manager
├── models.py                # Pydantic message types
├── tools_stock.py           # Stock market tools (yfinance)
├── tools_email_calendar.py  # Email + calendar tools
├── tools_travel.py          # Travel tools
├── providers/               # Email/calendar data providers (mock, zoho, google)
├── prompts/
│   ├── system.md            # Main system prompt (tool discipline, canvas awareness)
│   ├── a2ui_catalog.md      # A2UI component catalog for the agent
│   ├── design_system.md     # Floating window design system
│   ├── widget_templates.md  # Widget template examples
│   └── persona_context.md   # Mike's persona context
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
└── tauri-app/
    ├── src/
    │   ├── App.tsx              # CopilotKit provider + layout
    │   ├── main.tsx             # React entry
    │   ├── components/
    │   │   ├── Dashboard.tsx    # Floating window manager + useRenderToolCall
    │   │   ├── ChatPanel.tsx    # CopilotChat wrapper
    │   │   ├── A2UIRenderer.tsx # Declarative component tree renderer
    │   │   ├── componentMap.ts  # Component type → React component mapping
    │   │   └── aios/            # Individual A2UI components (Clock, Card, etc.)
    │   └── theme/
    │       └── aios.css         # Dark glassmorphic theme + floating window styles
    ├── src-tauri/               # Rust Tauri shell (Docker lifecycle management)
    ├── vite.config.ts           # Vite config (port 7100, proxy to 7101)
    ├── start-dev.sh             # One-command dev startup
    ├── package.json
    └── tsconfig.json

data/
└── personas/mike/
    ├── persona.json         # Mike's profile, preferences, stock watchlist
    ├── emails.json          # Mock email data
    ├── calendar.json        # Mock calendar data
    └── credentials.json     # Mock credentials
```

## After Making Changes

- **Backend (Python) changes**: Rebuild Docker and restart container
  ```bash
  docker build -t astra-agent PoC/astra-poc-vc/
  docker stop astra-agent; docker rm astra-agent; docker run -d --name astra-agent --env-file PoC/astra-poc-vc/.env -p 7101:8000 -v "$(pwd)/data:/app/data:ro" astra-agent
  ```
- **Frontend (React) changes**: Vite hot-reloads automatically
- **Tauri (Rust) changes**: `cargo tauri dev` auto-rebuilds

## License

See [LICENSE](LICENSE).
