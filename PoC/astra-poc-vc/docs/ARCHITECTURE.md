# AstraOS Architecture

> **Intelligent Personal OS with Persistent Memory, Learned Workflows & Proactive Intelligence**

---

## Executive Summary

AstraOS is an AI-powered personal operating system that learns from user behavior, maintains persistent context across sessions, and proactively surfaces relevant information. Unlike traditional assistants that start fresh each conversation, AstraOS builds an ever-growing understanding of the user's work, preferences, and patterns.

**Core Capabilities:**
- **Persistent Memory** — Remembers preferences, past interactions, and context across sessions
- **Domain Intelligence** — Routes queries to relevant context without mixing unrelated information
- **Learned Workflows** — Detects repeated patterns and offers to automate them
- **File Awareness** — Indexes and surfaces relevant documents when needed
- **Proactive Insights** — Connects dots across domains when genuine links exist

---

## System Architecture

```
┌──────────────────────────────────────────────────────────────────────────────────────┐
│                                    FRONTEND LAYER                                     │
│                                                                                       │
│                          ┌─────────────────────────────────┐                          │
│                          │         Tauri Desktop App       │                          │
│                          │                                 │                          │
│                          │   • CopilotKit UI (React)       │                          │
│                          │   • Fullscreen kiosk mode       │                          │
│                          │   • WebKitGTK renderer          │                          │
│                          └───────────────┬─────────────────┘                          │
│                                          │                                            │
│                              WebSocket / AG-UI Protocol                               │
└──────────────────────────────────────────┼───────────────────────────────────────────┘
                                           │
┌──────────────────────────────────────────┼───────────────────────────────────────────┐
│                                    AGENT LAYER                                        │
│                                           │                                           │
│  ┌────────────────────────────────────────┴────────────────────────────────────────┐ │
│  │                         LangGraph Agent (agent.py)                               │ │
│  │                                                                                  │ │
│  │   ┌──────────────┐      ┌──────────────┐      ┌──────────────┐                  │ │
│  │   │  chatbot     │ ───► │    tools     │ ───► │   memory     │                  │ │
│  │   │    node      │      │     node     │      │   extract    │                  │ │
│  │   └──────────────┘      └──────────────┘      └──────────────┘                  │ │
│  │          │                     │                     │                           │ │
│  │          ▼                     ▼                     ▼                           │ │
│  │   ┌─────────────────────────────────────────────────────────────────────────┐   │ │
│  │   │                    CONTEXT INJECTION LAYER                               │   │ │
│  │   │                                                                          │   │ │
│  │   │   ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐        │   │ │
│  │   │   │   Domain   │  │   Memory   │  │    File    │  │  Workflow  │        │   │ │
│  │   │   │   Router   │  │  Manager   │  │   Index    │  │   Engine   │        │   │ │
│  │   │   └─────┬──────┘  └─────┬──────┘  └─────┬──────┘  └─────┬──────┘        │   │ │
│  │   │         │               │               │               │               │   │ │
│  │   │         └───────────────┴───────────────┴───────────────┘               │   │ │
│  │   │                                │                                         │   │ │
│  │   └────────────────────────────────┼─────────────────────────────────────────┘   │ │
│  │                                    │                                             │ │
│  └────────────────────────────────────┼─────────────────────────────────────────────┘ │
│                                       │                                               │
│  ┌────────────────────────────────────┴─────────────────────────────────────────────┐ │
│  │                              TOOL REGISTRY                                        │ │
│  │                                                                                   │ │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ │ │
│  │  │   Email &   │ │   Stock &   │ │   Travel    │ │    File     │ │   Memory    │ │ │
│  │  │  Calendar   │ │   Finance   │ │   Tools     │ │   Tools     │ │   Tools     │ │ │
│  │  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘ │ │
│  │                                                                                   │ │
│  └───────────────────────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────┬───────────────────────────────────────────┘
                                           │
┌──────────────────────────────────────────┼───────────────────────────────────────────┐
│                                   DATA LAYER                                          │
│                                           │                                           │
│  ┌───────────────────┐  ┌───────────────────┐  ┌───────────────────┐                 │
│  │     Qdrant        │  │   External APIs   │  │   File System     │                 │
│  │  (Vector Store)   │  │                   │  │                   │                 │
│  │                   │  │  • Email (IMAP)   │  │  data/personas/   │                 │
│  │  Collections:     │  │  • Calendar       │  │    mike/files/    │                 │
│  │  • memories       │  │  • yfinance       │  │                   │                 │
│  │  • file_index     │  │  • Weather        │  │  • PDFs           │                 │
│  │                   │  │  • Flights        │  │  • Markdown       │                 │
│  │                   │  │                   │  │  • Images         │                 │
│  └───────────────────┘  └───────────────────┘  └───────────────────┘                 │
│                                                                                       │
└───────────────────────────────────────────────────────────────────────────────────────┘
                                           │
┌──────────────────────────────────────────┼───────────────────────────────────────────┐
│                              OBSERVABILITY LAYER                                      │
│                                           │                                           │
│  ┌───────────────────┐  ┌───────────────────┐  ┌───────────────────┐                 │
│  │     Langfuse      │  │   Logging         │  │   Health Check    │                 │
│  │   (Tracing)       │  │   (Structured)    │  │   (/health)       │                 │
│  │                   │  │                   │  │                   │                 │
│  │  • Token usage    │  │  • Agent events   │  │  • Readiness      │                 │
│  │  • Context size   │  │  • Tool calls     │  │  • Liveness       │                 │
│  │  • Latency        │  │  • Errors         │  │                   │                 │
│  │  • Sessions       │  │                   │  │                   │                 │
│  └───────────────────┘  └───────────────────┘  └───────────────────┘                 │
│                                                                                       │
└───────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Data Flow

### 1. User Message Flow

```
┌─────────┐     ┌───────────┐     ┌─────────────┐     ┌──────────────┐     ┌─────────┐
│  User   │────►│  Domain   │────►│   Memory    │────►│    Agent     │────►│ Response│
│ Message │     │  Router   │     │  Retrieval  │     │     LLM      │     │   UI    │
└─────────┘     └───────────┘     └─────────────┘     └──────────────┘     └─────────┘
                     │                   │                   │
                     ▼                   ▼                   ▼
              ┌───────────┐       ┌───────────┐       ┌───────────┐
              │ Classify  │       │ Top-3     │       │ Tool      │
              │ domains:  │       │ memories  │       │ calls     │
              │ [finance] │       │ Top-2     │       │ executed  │
              │           │       │ files     │       │           │
              └───────────┘       └───────────┘       └───────────┘
                                                            │
                                                            ▼
                                                      ┌───────────┐
                                                      │  Memory   │
                                                      │ extraction│
                                                      │ + logging │
                                                      └───────────┘
```

### 2. Email Polling Flow (Background)

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                        EMAIL POLLER (every 2 min)                            │
└──────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │  Fetch new emails   │
                         │  (IMAP/Zoho)        │
                         └──────────┬──────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
            ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
            │ Stock email │ │ Client email│ │ Other       │
            │ (Bloomberg) │ │ (Acme)      │ │             │
            └──────┬──────┘ └──────┬──────┘ └──────┬──────┘
                   │               │               │
                   ▼               ▼               ▼
        ┌──────────────────┐      │        ┌──────────────┐
        │ Check workflow:  │      │        │ Brief notify │
        │ bloomberg_alert  │      │        │              │
        │ enabled?         │      │        └──────────────┘
        └────────┬─────────┘      │
                 │                │
        ┌────────┴────────┐       │
        ▼                 ▼       │
   ┌─────────┐       ┌─────────┐  │
   │ AUTO    │       │ Manual  │  │
   │ execute │       │ notify  │  │
   │ workflow│       │ + offer │  │
   └────┬────┘       └────┬────┘  │
        │                 │       │
        ▼                 ▼       │
   ┌───────────────────────────────────────┐
   │  Pull context from memory/files       │
   │  (finance domain)                     │
   └───────────────────────────────────────┘
                    │
                    ▼
   ┌───────────────────────────────────────┐
   │  Render stock alert widget            │
   │  with enriched context                │
   └───────────────────────────────────────┘
```

---

## Component Deep Dives

### Domain Router

The domain router prevents context pollution by ensuring only relevant memories and files are retrieved.

```
                              USER INPUT
                                  │
                                  ▼
                    ┌─────────────────────────┐
                    │    DOMAIN CLASSIFIER    │
                    │                         │
                    │  1. Keyword scoring     │
                    │  2. Sender matching     │
                    │  3. Confidence check    │
                    └───────────┬─────────────┘
                                │
              ┌─────────────────┼─────────────────┐
              ▼                 ▼                 ▼
        ┌───────────┐     ┌───────────┐     ┌───────────┐
        │  FINANCE  │     │   SALES   │     │  TRAVEL   │
        │           │     │           │     │           │
        │ • stock   │     │ • deal    │     │ • flight  │
        │ • market  │     │ • pipeline│     │ • hotel   │
        │ • NVDA    │     │ • acme    │     │ • helsinki│
        │ • bloomberg│    │ • pricing │     │ • weather │
        └───────────┘     └───────────┘     └───────────┘
              │                 │                 │
              ▼                 ▼                 ▼
        ┌───────────┐     ┌───────────┐     ┌───────────┐
        │   TEAM    │     │ PERSONAL  │     │   ADMIN   │
        │           │     │           │     │           │
        │ • 1:1     │     │ • hobby   │     │ • remind  │
        │ • report  │     │ • weekend │     │ • todo    │
        │ • sarah   │     │ • gym     │     │ • schedule│
        └───────────┘     └───────────┘     └───────────┘
                                │
                                ▼
                    ┌─────────────────────────┐
                    │    BRIDGE DETECTION     │
                    │                         │
                    │  Only bridge if:        │
                    │  • Same person          │
                    │  • Same company         │
                    │  • Same date            │
                    │  • Related entity       │
                    └─────────────────────────┘
```

**Example Classifications:**
| Input | Domain(s) | Confidence |
|-------|-----------|------------|
| "Bloomberg email about NVDA" | `[finance]` | High |
| "Acme renewal pricing" | `[sales]` | High |
| "Helsinki trip weather" | `[travel]` | High |
| "Meeting with Sarah about Q1 pipeline" | `[team, sales]` | Medium (bridged) |
| "Remind me to check stocks" | `[admin, finance]` | Medium (bridged) |

---

### Memory Manager

Stores and retrieves memories with semantic search and domain filtering.

```
┌──────────────────────────────────────────────────────────────────┐
│                        MEMORY MANAGER                             │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                        STORE                                 │ │
│  │                                                              │ │
│  │   content ────► embed() ────► classify() ────► upsert()     │ │
│  │      │             │              │              │          │ │
│  │      │      ┌──────┴──────┐  ┌────┴────┐   ┌────┴─────┐    │ │
│  │      │      │ OpenAI      │  │ Domain  │   │  Qdrant  │    │ │
│  │      │      │ text-embed  │  │ Router  │   │  upsert  │    │ │
│  │      │      │ 3-small     │  │         │   │          │    │ │
│  │      │      │ (1536 dim)  │  │         │   │          │    │ │
│  │      │      └─────────────┘  └─────────┘   └──────────┘    │ │
│  │      │                                                      │ │
│  │      └─────► payload: {type, domains, tags, created_at}    │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                       RETRIEVE                               │ │
│  │                                                              │ │
│  │   query ────► embed() ────► filter(domains) ────► search()  │ │
│  │                                    │                │        │ │
│  │                             ┌──────┴──────┐   ┌─────┴─────┐ │ │
│  │                             │  Only match │   │  Semantic │ │ │
│  │                             │  memories   │   │  ranking  │ │ │
│  │                             │  in domain  │   │  top-5    │ │ │
│  │                             └─────────────┘   └───────────┘ │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                    AUTO-EXTRACTION                           │ │
│  │                                                              │ │
│  │   Pattern                          │  Memory Type            │ │
│  │   ─────────────────────────────────┼─────────────            │ │
│  │   "I prefer morning meetings"      │  fact                   │ │
│  │   "Remind me to call John"         │  reminder               │ │
│  │   "We decided to go with plan A"   │  episode                │ │
│  │   "Don't show me travel alerts"    │  fact (dismissal)       │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                   │
└──────────────────────────────────────────────────────────────────┘
```

**Memory Schema:**
```json
{
  "id": "uuid",
  "vector": [1536 floats],
  "payload": {
    "persona_id": "mike",
    "type": "fact | episode | reminder",
    "domains": ["finance", "sales"],
    "content": "Mike prefers Acme pricing tier 2 for deals over 50 seats",
    "tags": ["pricing", "acme"],
    "created_at": "2024-01-15T10:30:00Z",
    "access_count": 5
  }
}
```

---

### Workflow Engine

Detects repeated action patterns and proposes automation.

```
┌──────────────────────────────────────────────────────────────────┐
│                       WORKFLOW ENGINE                             │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│  SEED WORKFLOWS (pre-loaded)                                     │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  bloomberg_stock_alert                                      │  │
│  │  ├─ trigger: email_from:bloomberg                          │  │
│  │  ├─ actions: [analyze_stock, get_quote, emit_alert]        │  │
│  │  ├─ enabled: false                                         │  │
│  │  └─ hit_count: 1 (one more = propose)                      │  │
│  │                                                             │  │
│  │  meeting_prep                                               │  │
│  │  ├─ trigger: calendar_event_soon                           │  │
│  │  ├─ actions: [search_memory, search_files, emit_prep]      │  │
│  │  ├─ enabled: false                                         │  │
│  │  └─ hit_count: 0                                           │  │
│  │                                                             │  │
│  │  morning_briefing                                           │  │
│  │  ├─ trigger: session_start                                 │  │
│  │  ├─ actions: [list_emails, list_calendar, get_watchlist]   │  │
│  │  ├─ enabled: true (always on)                              │  │
│  │  └─ hit_count: 0                                           │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                   │
│  PATTERN DETECTION                                               │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │                                                             │  │
│  │   Turn 1: trigger=email_bloomberg                          │  │
│  │           actions=[analyze_stock, get_quote, emit_ui]      │  │
│  │                          │                                  │  │
│  │   Turn 2: trigger=email_bloomberg                          │  │
│  │           actions=[analyze_stock, get_quote, emit_ui]      │  │
│  │                          │                                  │  │
│  │                          ▼                                  │  │
│  │              ┌─────────────────────┐                       │  │
│  │              │  PATTERN DETECTED!  │                       │  │
│  │              │  Same trigger +     │                       │  │
│  │              │  Same actions       │                       │  │
│  │              │  2+ times           │                       │  │
│  │              └──────────┬──────────┘                       │  │
│  │                         │                                   │  │
│  │                         ▼                                   │  │
│  │   ┌─────────────────────────────────────────────────────┐  │  │
│  │   │  🔄 Workflow Suggestion                              │  │  │
│  │   │                                                      │  │  │
│  │   │  I noticed that when a Bloomberg email arrives,     │  │  │
│  │   │  you always want stock analysis and alerts.         │  │  │
│  │   │                                                      │  │  │
│  │   │  Want me to do this automatically?                  │  │  │
│  │   │                                                      │  │  │
│  │   │  [Enable]  [Not Now]                                │  │  │
│  │   └─────────────────────────────────────────────────────┘  │  │
│  │                                                             │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                   │
│  WORKFLOW LIFECYCLE                                              │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │                                                             │  │
│  │   OBSERVE ──► DETECT ──► PROPOSE ──► ENABLE ──► EXECUTE   │  │
│  │      │          │           │          │           │       │  │
│  │   Log every   Check      Render     Store in    Run auto  │  │
│  │   action      patterns   widget     Qdrant      on trigger│  │
│  │                                                             │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                   │
└──────────────────────────────────────────────────────────────────┘
```

---

### File Indexing

Indexes user files for semantic search and domain-aware retrieval.

```
┌──────────────────────────────────────────────────────────────────┐
│                        FILE INDEXING                              │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│  STARTUP PIPELINE                                                │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │                                                             │  │
│  │   data/personas/mike/files/                                │  │
│  │   ├── Q1_Pipeline_Report.md      ──► [sales, team]        │  │
│  │   ├── Acme_Pricing_Tiers.md      ──► [sales]              │  │
│  │   ├── Helsinki_Travel_Guide.md   ──► [travel]             │  │
│  │   ├── NovaTech_Demo_Notes.md     ──► [sales]              │  │
│  │   └── Board_Deck_Q1_Draft.md     ──► [team, sales]        │  │
│  │                                                             │  │
│  │              │                                              │  │
│  │              ▼                                              │  │
│  │   ┌─────────────────────────────────────────────────────┐  │  │
│  │   │  For each file:                                      │  │  │
│  │   │  1. Read content (markdown/text)                     │  │  │
│  │   │  2. Extract summary (first 600 chars)                │  │  │
│  │   │  3. Classify domains via DomainRouter               │  │  │
│  │   │  4. Embed filename + summary                         │  │  │
│  │   │  5. Store in Qdrant file_index collection           │  │  │
│  │   └─────────────────────────────────────────────────────┘  │  │
│  │                                                             │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                   │
│  FILE TOOLS                                                      │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │                                                             │  │
│  │  list_user_files(directory?)                               │  │
│  │  ├─ Returns: filename, type, size, domain tags            │  │
│  │  └─ Use case: "What files do I have?"                     │  │
│  │                                                             │  │
│  │  read_user_file(filename)                                  │  │
│  │  ├─ Returns: full file content                            │  │
│  │  └─ Use case: "Show me the Acme pricing"                  │  │
│  │                                                             │  │
│  │  search_user_files(query)                                  │  │
│  │  ├─ Semantic search + domain filtering                    │  │
│  │  └─ Use case: "Find docs about NovaTech"                  │  │
│  │                                                             │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                   │
└──────────────────────────────────────────────────────────────────┘
```

---

## Observability (Langfuse Integration)

```
┌──────────────────────────────────────────────────────────────────┐
│                    LANGFUSE TRACE STRUCTURE                       │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│  astra_turn (trace)                                              │
│  ├─ session_id: "abc-123"                                        │
│  ├─ user_id: "mike"                                              │
│  ├─ tags: ["astra", "email_bloomberg"]                           │
│  │                                                                │
│  ├─ chatbot_llm (generation)                                     │
│  │   ├─ model: "gpt-4o-mini"                                     │
│  │   ├─ input: [full message array]                              │
│  │   ├─ output: "Here's the stock analysis..."                   │
│  │   ├─ usage: {input: 1200, output: 350, total: 1550}          │
│  │   │                                                            │
│  │   └─ metadata:                                                 │
│  │       ├─ context_breakdown:                                   │
│  │       │   ├─ base_system_chars: 2500                          │
│  │       │   ├─ ui_catalog_chars: 1200                           │
│  │       │   ├─ memory_ctx_chars: 450                            │
│  │       │   ├─ memories_retrieved: 3                            │
│  │       │   ├─ files_retrieved: 2                               │
│  │       │   ├─ domains: ["finance"]                             │
│  │       │   └─ estimated_system_tokens: 1037                    │
│  │       │                                                        │
│  │       └─ tool_calls: [{name: "get_stock_quote", args: {...}}] │
│  │                                                                │
│  └─ context_injection (span)                                     │
│      ├─ base_system_tokens: 625                                  │
│      ├─ ui_catalog_tokens: 300                                   │
│      ├─ memory_tokens: 112                                       │
│      ├─ memories_count: 3                                        │
│      ├─ files_count: 2                                           │
│      └─ domains: ["finance"]                                     │
│                                                                   │
│  tool_execution (separate trace)                                 │
│  ├─ tools_called: ["get_stock_quote", "emit_ui"]                 │
│  ├─ duration_ms: 245                                             │
│  │                                                                │
│  ├─ tool:get_stock_quote (span)                                  │
│  │   ├─ args: {ticker: "NVDA"}                                   │
│  │   └─ is_data_tool: true                                       │
│  │                                                                │
│  └─ tool:emit_ui (span)                                          │
│      ├─ args: {surface_id: "stock-alert"}                        │
│      └─ is_data_tool: false                                      │
│                                                                   │
└──────────────────────────────────────────────────────────────────┘
```

**Key Metrics to Monitor:**
| Metric | What it tells you |
|--------|-------------------|
| `estimated_system_tokens` | Is context growing too large? |
| `memories_retrieved` | Are memories being found? |
| `files_retrieved` | Are files being surfaced? |
| `domains` | Is classification correct? |
| `tool_calls` | What actions are being taken? |
| `duration_ms` | Performance bottlenecks? |

---

## Configuration

### Environment Variables

```bash
# Core
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini

# Memory Store
QDRANT_URL=http://localhost:6333

# Email Polling
EMAIL_POLL_INTERVAL=120             # seconds (default: 2 min)
MIKE_EMAIL=mike@example.com
MIKE_EMAIL_PASSWORD=...
MIKE_EMAIL_PROVIDER=zoho            # or gmail

# Observability
LANGFUSE_ENABLED=1
LANGFUSE_PUBLIC_KEY=pk-...
LANGFUSE_SECRET_KEY=sk-...
LANGFUSE_HOST=http://localhost:3000
```

---

## File Structure

```
PoC/astra-poc-vc/
├── agent.py              # LangGraph agent with memory + workflow integration
├── main.py               # FastAPI server, email poller, WebSocket
├── memory.py             # MemoryManager + Qdrant client
├── domain_router.py      # Domain classification
├── workflow_engine.py    # Pattern detection + workflow management
├── tools_files.py        # File tools + indexing
├── tools_memory.py       # Memory + workflow tools
├── tools_stock.py        # Stock/finance tools
├── tools_email_calendar.py
├── tools_travel.py
├── prompts/
│   ├── system.md         # Base system prompt
│   ├── persona_context.md # Mike's persona
│   └── a2ui_catalog.md   # UI component catalog
├── data/
│   └── personas/
│       └── mike/
│           ├── files/    # User's documents
│           └── ...
├── docker-compose.yml
└── requirements.txt
```

---

## Current Implementation Status

| Component | Status | Notes |
|-----------|--------|-------|
| Qdrant Integration | ✅ Done | With in-memory fallback |
| Domain Router | ✅ Done | 6 domains, bridging logic |
| Memory Manager | ✅ Done | Store, retrieve, file index |
| File Tools | ✅ Done | list, read, search |
| Memory Tools | ✅ Done | store, search, workflow tools |
| Workflow Engine | ✅ Done | Pattern detection, proposals |
| Agent Integration | ✅ Done | Context injection, extraction |
| Email Poller | ✅ Done | 2 min interval, workflow-aware |
| Langfuse Tracing | ✅ Done | Full context breakdown |
| Morning Briefing | ⏳ Partial | Basic, needs domain routing |
| Creative Behaviors | ⏳ Partial | In system prompt, not proactive |

---

## Bare Metal Deployment (AstraOS Appliance)

AstraOS can be packaged as a minimal Linux appliance — just kernel, shell, and the Tauri desktop app. No desktop environment, no window manager, no package manager.

**Single deployment mode: Fullscreen Desktop (~300-350 MB)**

### Desktop Appliance Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      ASTRA KIOSK APPLIANCE                                   │
│                          (~300-400 MB)                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                          DISPLAY LAYER                                  │ │
│  │                                                                         │ │
│  │  ┌─────────────────────────────────────────────────────────────────┐   │ │
│  │  │                     TAURI APP (FULLSCREEN)                       │   │ │
│  │  │                                                                  │   │ │
│  │  │   ┌──────────────────────────────────────────────────────────┐  │   │ │
│  │  │   │                    ASTRA UI (React)                       │  │   │ │
│  │  │   │                                                           │  │   │ │
│  │  │   │   • CopilotKit chat interface                            │  │   │ │
│  │  │   │   • Dashboard widgets                                     │  │   │ │
│  │  │   │   • No window decorations, no taskbar                    │  │   │ │
│  │  │   │   • Touch-friendly (optional)                            │  │   │ │
│  │  │   │                                                           │  │   │ │
│  │  │   └──────────────────────────────────────────────────────────┘  │   │ │
│  │  │                              │                                   │   │ │
│  │  │                      WebKitGTK (~50 MB)                         │   │ │
│  │  └──────────────────────────────┼──────────────────────────────────┘   │ │
│  │                                 │                                       │ │
│  │  ┌──────────────────────────────┴──────────────────────────────────┐   │ │
│  │  │                      CAGE (Wayland Kiosk)                        │   │ │
│  │  │                          (~500 KB)                               │   │ │
│  │  │                                                                  │   │ │
│  │  │   • Single-app Wayland compositor                               │   │ │
│  │  │   • Fullscreen only, no window management                       │   │ │
│  │  │   • Runs directly on DRM/KMS (no X11)                           │   │ │
│  │  │   • Usage: cage -- /opt/astra/astra-ui                          │   │ │
│  │  └──────────────────────────────────────────────────────────────────┘   │ │
│  │                                 │                                       │ │
│  └─────────────────────────────────┼───────────────────────────────────────┘ │
│                                    │                                         │
│  ┌─────────────────────────────────┴───────────────────────────────────────┐ │
│  │                          BACKEND SERVICES                                │ │
│  │                                                                          │ │
│  │   ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────┐ │ │
│  │   │   ASTRA AGENT   │  │     QDRANT      │  │   LOCAL SOCKETS         │ │ │
│  │   │                 │  │                 │  │                         │ │ │
│  │   │  Python 3.11+   │  │  Static binary  │  │  localhost:8000 (API)   │ │ │
│  │   │  FastAPI        │  │  Vector store   │  │  localhost:6333 (DB)    │ │ │
│  │   │  LangGraph      │  │                 │  │                         │ │ │
│  │   └─────────────────┘  └─────────────────┘  └─────────────────────────┘ │ │
│  │                                                                          │ │
│  └──────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                          MINIMAL USERSPACE                              │ │
│  │                                                                         │ │
│  │   • Busybox (~2 MB) — shell + core utils                               │ │
│  │   • musl libc (~1 MB)                                                  │ │
│  │   • Mesa DRI drivers (~20-40 MB) — GPU acceleration                    │ │
│  │   • libinput (~1 MB) — keyboard/mouse/touch input                      │ │
│  │   • wlroots (~2 MB) — Wayland compositor library                       │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                          LINUX KERNEL                                   │ │
│  │                           (~15-20 MB)                                   │ │
│  │                                                                         │ │
│  │   Kiosk config requires:                                               │ │
│  │   • DRM/KMS (direct rendering)                                         │ │
│  │   • GPU driver (i915, amdgpu, nouveau, or vc4 for RPi)                 │ │
│  │   • Evdev (input devices)                                              │ │
│  │   • Network stack                                                       │ │
│  │   • Framebuffer console (fallback)                                     │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                            HARDWARE                                     │ │
│  │                                                                         │ │
│  │   • Display (HDMI/DP/eDP)        • Keyboard (USB/Bluetooth)            │ │
│  │   • GPU (Intel/AMD/RPi/NVIDIA)   • Mouse/Touch (optional)              │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Kiosk Boot Sequence

```
  BIOS/UEFI
      │
      ▼
  ┌─────────┐
  │ Kernel  │  Load vmlinuz + initramfs
  └────┬────┘
       │
       ▼
  ┌─────────┐
  │  Init   │  /init script
  └────┬────┘
       │
       ├──► Mount filesystems
       │
       ├──► Load GPU driver (modprobe i915/amdgpu/vc4)
       │
       ├──► Start Qdrant (background)
       │
       ├──► Start Astra API (background)
       │
       ├──► Wait for services ready
       │
       └──► exec cage -- /opt/astra/astra-ui
                   │
                   ▼
            ┌─────────────────────────────┐
            │                             │
            │      FULLSCREEN ASTRA       │
            │                             │
            │   No desktop, no taskbar    │
            │   Just the app              │
            │                             │
            └─────────────────────────────┘
```

**Kiosk /init script:**
```bash
#!/bin/sh
mount -t proc proc /proc
mount -t sysfs sys /sys
mount -t devtmpfs dev /dev

# GPU setup
modprobe drm
modprobe i915  # or amdgpu, vc4 (RPi), etc.

# Mount persistent storage
mount /dev/sda2 /data 2>/dev/null

# Load config
[ -f /data/.env ] && export $(cat /data/.env | xargs)

# Start backend services
/opt/qdrant/qdrant --storage-path /data/qdrant &
sleep 2
cd /opt/astra && python -m uvicorn main:app --host 127.0.0.1 --port 8000 &
sleep 3

# Launch fullscreen Tauri app via Cage compositor
export XDG_RUNTIME_DIR=/tmp
export WLR_LIBINPUT_NO_DEVICES=1  # optional: ignore if no input yet
exec cage -s -- /opt/astra/astra-ui
```

### Size Breakdown

| Component | Size | Notes |
|-----------|------|-------|
| Linux kernel | 18 MB | With GPU/DRM drivers |
| Busybox | 2 MB | Shell + core utilities |
| musl + SSL | 4 MB | libc + HTTPS support |
| Python + deps | 80 MB | FastAPI, LangGraph, etc. |
| Qdrant | 45 MB | Vector store |
| Astra code | 1 MB | Application code |
| Cage | 0.5 MB | Kiosk compositor |
| wlroots | 2 MB | Wayland library |
| Mesa DRI | 30 MB | GPU drivers |
| WebKitGTK | 50 MB | Tauri renderer |
| Tauri binary | 15 MB | Compiled desktop app |
| libinput | 1 MB | Input handling |
| GTK4 + deps | 40 MB | UI toolkit |
| **TOTAL** | **~300 MB** | Uncompressed |
| **Compressed** | **~180 MB** | squashfs image |

### Size Breakdown

| Component | Size | Notes |
|-----------|------|-------|
| Linux kernel | 8-15 MB | Minimal config, compressed |
| Busybox | 1-2 MB | Shell + core utilities |
| musl libc | 1 MB | Lightweight C library |
| OpenSSL + CA certs | 3-4 MB | Required for HTTPS |
| Python 3.11 (minimal) | 40-50 MB | Stripped, no test/docs |
| Python deps | 30-40 MB | FastAPI, LangGraph, etc. |
| Qdrant | 40-50 MB | Static binary |
| Astra app code | 1 MB | Your Python code |
| **TOTAL** | **~150-200 MB** | Bootable image |

With compression (squashfs): **~80-120 MB**

### Boot Sequence

```
┌─────────────────────────────────────────────────────────────────┐
│                        BOOT SEQUENCE                             │
└─────────────────────────────────────────────────────────────────┘

  BIOS/UEFI
      │
      ▼
  ┌─────────┐
  │ Kernel  │  Load from /boot/vmlinuz
  └────┬────┘
       │
       ▼
  ┌─────────┐
  │  Init   │  /init (simple shell script)
  └────┬────┘
       │
       ├──► Mount filesystems (/data for persistence)
       │
       ├──► Load environment (.env with API keys)
       │
       ├──► Start Qdrant (background, :6333)
       │
       ├──► Wait for Qdrant ready
       │
       └──► Start Astra agent (uvicorn :8000)
              │
              ▼
         Ready in ~5-10 seconds
         Listening on http://0.0.0.0:8000
```

**Example /init script:**
```bash
#!/bin/sh
mount -t proc proc /proc
mount -t sysfs sys /sys
mount -t devtmpfs dev /dev

# Mount persistent storage
mount /dev/sda2 /data 2>/dev/null || echo "No persistent storage"

# Load config
[ -f /data/.env ] && export $(cat /data/.env | xargs)

# Start Qdrant
/opt/qdrant/qdrant --storage-path /data/qdrant &

# Wait for Qdrant
sleep 2

# Start Astra
cd /opt/astra
exec /opt/python/bin/python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

### Distribution Formats

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                      DISTRIBUTION OPTIONS (Desktop Only)                      │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  ┌─────────────────────┐   astra-desktop.img                                 │
│  │  RAW IMAGE (.img)   │   ~300-350 MB                                       │
│  │                     │                                                      │
│  │  dd to USB/SD card  │   Best for: Raspberry Pi, SBCs, dedicated hardware │
│  └─────────────────────┘   Deploy: dd if=astra.img of=/dev/sdX bs=4M        │
│                                                                               │
│  ┌─────────────────────┐   astra-desktop.qcow2                               │
│  │  VM IMAGE (qcow2)   │   ~200 MB sparse                                    │
│  │                     │                                                      │
│  │  QEMU/Proxmox/KVM   │   Best for: Testing, VM-based kiosks               │
│  └─────────────────────┘   Requires: virtio-gpu passthrough                  │
│                                                                               │
│  ┌─────────────────────┐   astra-desktop.iso                                 │
│  │  ISO (.iso)         │   ~250 MB                                           │
│  │                     │                                                      │
│  │  Bootable installer │   Best for: Any x86_64/ARM64 machine with GPU      │
│  └─────────────────────┘   Deploy: Boot and install to disk                  │
│                                                                               │
└──────────────────────────────────────────────────────────────────────────────┘
```

**Deployment Examples:**

```bash
# Flash to SD card (Raspberry Pi 4/5)
dd if=astra-desktop-rpi4.img of=/dev/sdX bs=4M status=progress

# Flash to USB drive (Intel NUC, mini PC)
dd if=astra-desktop-x86_64.img of=/dev/sdX bs=4M status=progress

# Boot VM with GPU passthrough
qemu-system-x86_64 -enable-kvm -m 2G -cpu host \
  -drive file=astra-desktop.qcow2 \
  -device virtio-gpu-pci \
  -display gtk,gl=on
```

### Deployment Topologies

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                         TOPOLOGY OPTIONS                                      │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  OPTION A: KIOSK (Self-Contained Terminal)                                   │
│  ─────────────────────────────────────────                                   │
│                                                                               │
│    ┌───────────────────────────────────────────┐                             │
│    │          ASTRA KIOSK DEVICE               │                             │
│    │                                           │                             │
│    │   ┌───────────────────────────────────┐   │                             │
│    │   │         TAURI FULLSCREEN          │   │    User interacts           │
│    │   │                                   │   │◄── directly with            │
│    │   │   Chat │ Dashboard │ Widgets      │   │    the device               │
│    │   └───────────────┬───────────────────┘   │                             │
│    │                   │ localhost              │                             │
│    │   ┌───────────────┴───────────────────┐   │                             │
│    │   │  Astra Agent + Qdrant (internal)  │   │                             │
│    │   └───────────────────────────────────┘   │                             │
│    │                   │                        │                             │
│    │                   ▼                        │                             │
│    │            OpenAI API (internet)          │                             │
│    └───────────────────────────────────────────┘                             │
│                                                                               │
│    Use cases:                                                                │
│    • Personal AI terminal on desk                                            │
│    • Dedicated assistant kiosk                                               │
│    • Raspberry Pi + touchscreen                                              │
│    • Repurposed laptop                                                       │
│                                                                               │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  OPTION B: MULTI-DEVICE (Shared Backend)                                     │
│  ────────────────────────────────────────                                    │
│                                                                               │
│    ┌───────────────────────────────────────────┐                             │
│    │          ASTRA KIOSK (Primary)            │                             │
│    │                                           │                             │
│    │   ┌───────────────────────────────────┐   │                             │
│    │   │         TAURI FULLSCREEN          │   │   Main workstation          │
│    │   └───────────────────────────────────┘   │                             │
│    │                   │                        │                             │
│    │   ┌───────────────┴───────────────────┐   │                             │
│    │   │  Astra Agent + Qdrant             │   │   Shared memory/context     │
│    │   │  :8000 exposed to LAN             │   │                             │
│    │   └───────────────────────────────────┘   │                             │
│    └───────────────────────────────────────────┘                             │
│                         ▲                                                     │
│                         │ LAN                                                │
│              ┌──────────┴──────────┐                                         │
│              │                     │                                         │
│       ┌──────┴──────┐       ┌──────┴──────┐                                  │
│       │ Laptop      │       │ Secondary   │  Other Tauri desktops            │
│       │ (Tauri)     │       │ (Tauri)     │  connect to same backend         │
│       └─────────────┘       └─────────────┘                                  │
│                                                                               │
│    Use cases:                                                                │
│    • Multiple desktops, shared memory                                        │
│    • Laptop + desktop same context                                           │
│    • Home office setup                                                       │
│                                                                               │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Why Cage for Kiosk?

```
┌──────────────────────────────────────────────────────────────────┐
│                   WAYLAND COMPOSITOR OPTIONS                      │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐               │
│  │    CAGE     │  │    SWAY     │  │   WESTON    │               │
│  │   (~500KB)  │  │   (~5MB)    │  │   (~3MB)    │               │
│  ├─────────────┤  ├─────────────┤  ├─────────────┤               │
│  │ Single app  │  │ Full WM     │  │ Reference   │               │
│  │ Fullscreen  │  │ Workspaces  │  │ compositor  │               │
│  │ No config   │  │ Config file │  │ Configurable│               │
│  │ No escape   │  │ Can escape  │  │ Can escape  │               │
│  │             │  │             │  │             │               │
│  │ PERFECT FOR │  │ Too much    │  │ Overkill    │               │
│  │ KIOSK MODE  │  │ for kiosk   │  │ for kiosk   │               │
│  └─────────────┘  └─────────────┘  └─────────────┘               │
│                                                                   │
│  Cage: https://github.com/cage-kiosk/cage                        │
│  - Runs exactly ONE app, fullscreen, no window decorations       │
│  - No way for user to escape to shell (secure kiosk)             │
│  - Tiny footprint, wlroots-based                                 │
│  - Usage: cage -- /path/to/app                                   │
│                                                                   │
└──────────────────────────────────────────────────────────────────┘
```

### Tauri Kiosk Configuration

```rust
// src-tauri/src/main.rs — Fullscreen kiosk mode
use tauri::Manager;

fn main() {
    tauri::Builder::default()
        .setup(|app| {
            let window = app.get_webview_window("main").unwrap();

            // Fullscreen, no decorations
            window.set_fullscreen(true)?;
            window.set_decorations(false)?;
            window.set_always_on_top(true)?;

            // Disable context menu, dev tools in production
            #[cfg(not(debug_assertions))]
            window.set_ignore_cursor_events(false)?;

            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error running tauri app");
}
```

```json
// src-tauri/tauri.conf.json
{
  "app": {
    "windows": [
      {
        "title": "AstraOS",
        "fullscreen": true,
        "decorations": false,
        "resizable": false,
        "alwaysOnTop": true,
        "focus": true
      }
    ]
  }
}
```

### Build Tools

| Tool | Purpose | Complexity |
|------|---------|------------|
| **Buildroot** | Custom embedded Linux, full control | Medium (recommended) |
| **Yocto** | Industrial embedded, reproducible | Hard |
| **Alpine + mkinitfs** | Minimal base, manual assembly | Medium |

**Buildroot: Recommended for Desktop Appliance**

Buildroot can produce a complete bootable image with Cage + Tauri:

```bash
# Clone buildroot
git clone https://github.com/buildroot/buildroot
cd buildroot

# Use defconfig for your target (e.g., RPi4)
make raspberrypi4_64_defconfig

# Enable required packages via menuconfig
make menuconfig
# → Target packages → Graphic libraries → mesa3d (DRI drivers)
# → Target packages → Graphic libraries → wlroots
# → Target packages → Graphic libraries → cage
# → Target packages → Interpreter languages → python3 + pip
# → System configuration → /dev management → devtmpfs + eudev

# Add custom overlay with Astra files
echo "BR2_ROOTFS_OVERLAY=\"overlay/\"" >> .config

# Build (takes 30-60 min first time)
make

# Output: output/images/sdcard.img (~300MB)
```

### Hardware Requirements

| Spec | Minimum | Recommended |
|------|---------|-------------|
| CPU | 2 cores | 4+ cores |
| RAM | 1 GB | 2-4 GB |
| Storage | 512 MB | 2+ GB (for memory persistence) |
| GPU | Intel/AMD/RPi (DRM/KMS) | Dedicated or good iGPU |
| Display | HDMI/DP/eDP | Any resolution |
| Network | Required | Ethernet preferred |

**Target devices:**
- Raspberry Pi 4/5 (vc4 GPU, good WebKit perf)
- Intel NUC (integrated GPU, perfect for kiosk)
- Old laptop/thin client (repurpose as terminal)
- Mini PCs (Beelink, GMKtec, etc.)
- Any x86_64/ARM64 with GPU + display output

### Security Considerations

```
┌──────────────────────────────────────────────────────────────────┐
│                     SECURITY MODEL                                │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│  READ-ONLY ROOT                                                  │
│  ├─ Root filesystem: squashfs (immutable)                        │
│  ├─ /data: writable partition for Qdrant + config                │
│  └─ Updates: replace entire image, reboot                        │
│                                                                   │
│  SECRETS                                                         │
│  ├─ API keys in /data/.env (not in image)                        │
│  ├─ Or: inject via environment at boot                           │
│  └─ Never bake secrets into the image                            │
│                                                                   │
│  NETWORK                                                         │
│  ├─ Firewall: only expose :8000 (and :22 if needed)              │
│  ├─ TLS: put behind nginx/caddy reverse proxy                    │
│  └─ Or: run on private network only                              │
│                                                                   │
└──────────────────────────────────────────────────────────────────┘
```
