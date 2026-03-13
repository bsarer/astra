# Design: Persistent Memory, Learned Workflows & Proactive Intelligence

## Overview
This design adds three interconnected systems to AstraOS: (1) a Qdrant-backed persistent memory store with domain-aware retrieval, (2) a learned workflow engine that discovers and automates user patterns, and (3) a mounted file system with intelligent indexing. Together, these eliminate the "Phase 2 wall" — the OS maintains its own context.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     AstraOS Agent (LangGraph)               │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ Domain Router │  │ Memory Tools │  │ File Tools       │  │
│  │              │  │              │  │                  │  │
│  │ classify()   │  │ store()      │  │ list_files()     │  │
│  │ retrieve()   │  │ search()     │  │ read_file()      │  │
│  │ bridge()     │  │ extract()    │  │ search_files()   │  │
│  └──────┬───────┘  └──────┬───────┘  └────────┬─────────┘  │
│         │                 │                    │            │
│  ┌──────┴─────────────────┴────────────────────┴─────────┐  │
│  │              Memory Manager (memory.py)                │  │
│  │                                                       │  │
│  │  • Embedding: OpenAI text-embedding-3-small           │  │
│  │  • Domain classification (keyword + fallback embed)   │  │
│  │  • Fact extraction from conversations                 │  │
│  │  • Workflow pattern detection                         │  │
│  │  • File indexing pipeline                             │  │
│  └───────────────────────┬───────────────────────────────┘  │
│                          │                                  │
└──────────────────────────┼──────────────────────────────────┘
                           │
              ┌────────────┴────────────┐
              │    Qdrant (port 6333)   │
              │                         │
              │  Collections:           │
              │   • memories            │
              │   • files               │
              │   • workflows           │
              └─────────────────────────┘
```


## Component Design

### 1. Qdrant Setup

**Docker Compose addition:**
```yaml
qdrant:
  image: qdrant/qdrant:latest
  ports:
    - "6333:6333"
  volumes:
    - qdrant_data:/qdrant/storage
```

**Collections:**

| Collection | Vector Size | Payload Fields |
|-----------|-------------|----------------|
| `memories` | 1536 (text-embedding-3-small) | `type`, `domains`, `content`, `tags`, `created_at`, `access_count`, `persona_id` |
| `files` | 1536 | `filename`, `path`, `domains`, `summary`, `file_type`, `indexed_at`, `persona_id` |
| `workflows` | 1536 | `name`, `trigger`, `actions`, `enabled`, `hit_count`, `created_at`, `persona_id` |

### 2. Domain Router (`domain_router.py`)

The domain router is the key innovation — it prevents irrelevant context from polluting responses.

**Domain Taxonomy:**
```python
DOMAINS = {
    "finance": {
        "keywords": ["stock", "market", "portfolio", "ticker", "AAPL", "MSFT", "NVDA",
                     "TSLA", "GOOG", "AMZN", "META", "earnings", "dividend", "bull",
                     "bear", "price target", "bloomberg", "trading", "investment",
                     "shares", "equity", "fund", "analyst", "upgrade", "downgrade"],
        "senders": ["bloomberg", "marketwatch", "cnbc", "wsj"],
        "file_patterns": ["*portfolio*", "*stock*", "*financial*", "*investment*"],
    },
    "sales": {
        "keywords": ["deal", "pipeline", "renewal", "pricing", "client", "prospect",
                     "quota", "revenue", "contract", "proposal", "acme", "bluepeak",
                     "novatech", "salesforce", "CRM", "onboarding", "expansion",
                     "discount", "seats", "tier"],
        "senders": ["acmecorp", "bluepeak", "novatech", "vertexsolutions"],
        "file_patterns": ["*pricing*", "*pipeline*", "*proposal*", "*deal*"],
    },
    "travel": {
        "keywords": ["flight", "hotel", "trip", "travel", "airport", "booking",
                     "itinerary", "packing", "weather", "helsinki", "finland",
                     "rome", "italy", "passport", "visa", "currency", "aurora"],
        "senders": ["finnair", "hotelkamp", "tripadvisor", "booking.com", "visitfinland"],
        "file_patterns": ["*travel*", "*guide*", "*itinerary*", "*packing*"],
    },
    "team": {
        "keywords": ["1:1", "team", "report", "SDR", "pipeline review", "all-hands",
                     "metrics", "leads", "MQL", "meetings booked", "performance"],
        "senders": ["sarah.chen", "jake.morrison", "priya.patel", "lisa.park"],
        "file_patterns": ["*team*", "*report*", "*metrics*", "*board*"],
    },
    "personal": {
        "keywords": ["hobby", "beer", "football", "hiking", "photography", "gym",
                     "crossfit", "weekend", "vacation"],
        "senders": [],
        "file_patterns": ["*photo*", "*personal*"],
    },
}
```

**Classification Algorithm:**
1. **Fast path (keyword match):** Score each domain by counting keyword hits in the input text. If one domain scores 3x higher than the next, use it directly.
2. **Sender match:** For emails, check sender against domain sender patterns. Direct match = high confidence.
3. **Ambiguous fallback:** If no clear winner, embed the query and compare against domain centroid embeddings (pre-computed from keyword lists). Pick top-1 or top-2 if scores are close (cross-domain bridge).

**Cross-Domain Bridging Rules:**
- Bridge is triggered when two domains both score above a threshold AND there's a temporal/entity link (same person, same date, same company mentioned in both).
- Example: "NVDA email" (finance) + "advisor meeting next week" (finance + sales) → bridge because NVDA is in holdings AND advisor is on calendar.
- Anti-example: "NVDA email" (finance) + "Helsinki trip" (travel) → NO bridge, no entity/temporal overlap.


### 3. Memory Manager (`memory.py`)

**Core class:**
```python
class MemoryManager:
    def __init__(self, qdrant_url, persona_id, embedding_model):
        self.client = QdrantClient(url=qdrant_url)
        self.persona_id = persona_id
        self.embedder = embedding_model  # OpenAI text-embedding-3-small
        self.domain_router = DomainRouter()

    async def store(self, content, memory_type, tags=None, domains=None):
        """Store a memory with auto-domain classification if domains not provided."""

    async def retrieve(self, query, domains=None, memory_type=None, limit=5):
        """Domain-filtered semantic retrieval."""

    async def extract_facts(self, conversation_messages):
        """Extract storable facts from a conversation turn."""

    async def detect_workflow_pattern(self, action_sequence):
        """Check if an action sequence matches a known pattern or creates a new one."""
```

**Fact Extraction Pipeline:**
After each agent response, run a lightweight extraction pass:
1. Did the user express a preference? → Store as `fact` with relevant domain
2. Did the user dismiss/accept a suggestion? → Store as `episode`
3. Did the agent perform a multi-step action? → Log as action sequence for workflow detection
4. Did the user mention a deadline or reminder? → Store as `reminder` with timestamp

This extraction uses a small prompt (not the main agent LLM) or rule-based patterns to keep it fast and cheap.

**Memory Decay:**
- Each memory has `access_count` and `created_at`
- Retrieval score = `semantic_similarity * recency_weight * access_bonus`
- `recency_weight` = `1.0 / (1 + days_since_creation * 0.05)` — gentle decay
- `access_bonus` = `1.0 + log(access_count + 1) * 0.1` — frequently accessed memories stay relevant

### 4. File System Tools (`tools_files.py`)

**Mounted directory:** `data/personas/mike/files/`

**Indexing pipeline (runs at startup):**
1. Walk the directory
2. For each file:
   - PDF → extract text via `PyPDF2` or `pdfplumber`
   - Markdown/Text → read directly
   - Images → store filename + any EXIF metadata (skip OCR for PoC, describe based on filename)
3. Generate summary (first 500 chars or LLM-generated if short)
4. Classify domains using DomainRouter
5. Embed summary and store in Qdrant `files` collection

**Tools:**
- `list_user_files(directory?)` → returns filenames, types, sizes, domain tags
- `read_user_file(path)` → returns content (text extraction for PDFs)
- `search_user_files(query)` → semantic search against file summaries in Qdrant, domain-filtered


### 5. Workflow Engine

**Pattern Detection:**
```python
# Action log (in-memory, persisted to Qdrant periodically)
action_log = [
    {"timestamp": "...", "trigger": "email_bloomberg", "actions": ["analyze_stock", "get_quote", "emit_ui_stock_alert"]},
    {"timestamp": "...", "trigger": "email_bloomberg", "actions": ["analyze_stock", "get_quote", "emit_ui_stock_alert"]},
    # ^ Pattern detected: same trigger -> same action sequence, 2+ times
]
```

**Workflow Lifecycle:**
1. **Observe:** Log every trigger+action sequence
2. **Detect:** After each action, check if this trigger+action combo has occurred 2+ times
3. **Propose:** Render a workflow proposal widget:
   ```
   ┌─────────────────────────────────────────┐
   │  🔄 Workflow Suggestion                  │
   │                                         │
   │  I noticed a pattern:                   │
   │  When a Bloomberg email arrives,        │
   │  you always want stock analysis.        │
   │                                         │
   │  Want me to do this automatically?      │
   │                                         │
   │  [Enable]  [Not Now]  [Never]           │
   └─────────────────────────────────────────┘
   ```
4. **Enable:** Store in Qdrant `workflows` collection with `enabled: true`
5. **Execute:** On matching trigger, run the workflow actions automatically
6. **Manage:** User can view/toggle workflows via "show my workflows" command

**Seed Workflows (pre-loaded for demo):**
- `bloomberg_stock_alert`: trigger=`email_from:bloomberg`, actions=`[analyze_stock, get_quote, emit_stock_alert]`, enabled=false, hit_count=1 (one more trigger auto-proposes)
- `meeting_prep`: trigger=`calendar_event_in:30min`, actions=`[search_memory_attendee, search_files_client, emit_prep_widget]`, enabled=false, hit_count=0
- `morning_briefing`: trigger=`session_start`, actions=`[list_emails, list_calendar, get_watchlist, emit_briefing]`, enabled=true (always on)

### 6. Creative Agent Behaviors

The "creative" layer is not a separate system — it's instructions in the system prompt that leverage the domain router and memory. The agent is told:

> When you retrieve context for a task, check if any retrieved memories or files create a CONNECTION to another domain that would be useful. If you find a genuine link (same person, same company, same date, related topic), enrich your response with that cross-domain insight. But only if the link is real — don't force connections.

**Concrete creative behaviors (prompt-driven):**

1. **Meeting + Email Correlation:** When preparing for a meeting, search memory for past interactions with attendees. If found, include "Last time you spoke with [person], they mentioned [topic]."

2. **File Surfacing:** When any task involves a client/topic, search files for matches. If a relevant PDF exists, mention it: "I found [filename] in your files — it covers [topic]. Want me to include it?"

3. **Proactive Suggestions:** After completing a task, check if there's an obvious next step the user hasn't asked for:
   - Rendered stock alert → check if advisor meeting is upcoming → suggest portfolio briefing
   - Prepared meeting notes → check if follow-up email is needed → draft it
   - Showed travel itinerary → check weather changed → alert if significant

4. **Drift Detection:** Track what the user HASN'T looked at recently:
   - Trip in 2 days but no travel-related queries → proactively surface itinerary
   - Board deck due in 3 days but no file access → remind
   - Client meeting tomorrow but no prep done → suggest prep


### 7. Demo File Contents

Create these files in `data/personas/mike/files/`:

**Q1_Pipeline_Report.pdf** — A 2-page sales pipeline summary with deal stages, revenue forecasts, and team performance metrics. Mentions Acme ($450K renewal), BluePeak ($280K in negotiation), NovaTech ($180K new business).

**Acme_Pricing_Tiers.pdf** — Pricing table: Starter ($15/seat/mo), Professional ($35/seat/mo), Enterprise ($55/seat/mo). Volume discounts: 50+ seats = 15% off, 100+ = 25% off. Includes onboarding timeline (2-4 weeks).

**Helsinki_Travel_Guide.pdf** — Quick guide: top restaurants, sauna etiquette, public transport (HSL app), useful Finnish phrases, photography spots for Northern Lights.

**NovaTech_Product_Demo_Notes.md** — Jake's notes from the demo: Dave Wilson impressed by API integration, wants Head of Product involved, potential close by end of March, key differentiator was real-time sync feature.

**Board_Deck_Q1_Draft.pdf** — Draft Q1 board presentation: revenue at 87% of target, 3 enterprise deals in pipeline, team expanded by 2, key risk is BluePeak delay.

**Team_Photo_Austin_Offsite.jpg** — A placeholder image (team offsite photo).

### 8. Integration Points

**Agent startup flow (enhanced):**
1. Initialize Qdrant connection
2. Index files (if not already indexed)
3. Load seed workflows
4. On first user connection → execute `morning_briefing` workflow
5. Morning briefing uses domain router: pull `team` context for meetings, `finance` for stocks, `travel` for trips — each in its own retrieval pass, not mixed

**Per-turn flow (enhanced):**
1. User message arrives
2. Domain router classifies intent → determines which domains to query
3. Retrieve top-5 memories from matching domain(s)
4. Retrieve top-2 files from matching domain(s)
5. Inject retrieved context into system prompt (max ~800 tokens)
6. Agent processes with enriched context
7. After response, extract facts and log action sequence
8. Check if action sequence triggers workflow detection

**Email poller flow (enhanced):**
1. New email arrives
2. Classify email domain
3. Check if any enabled workflow matches this trigger
4. If yes, execute workflow actions automatically
5. If no, but pattern detected (2+ similar triggers), propose workflow

## File Changes

| File | Change |
|------|--------|
| `memory.py` (new) | MemoryManager class, Qdrant client, embedding, fact extraction |
| `domain_router.py` (new) | Domain classification, cross-domain bridging |
| `tools_files.py` (new) | File system tools (list, read, search) |
| `tools_memory.py` (new) | Memory tools for the agent (store, search, workflows) |
| `agent.py` | Integrate memory retrieval into chatbot_node, add new tools, action logging |
| `main.py` | Initialize Qdrant on startup, file indexing, enhanced morning briefing |
| `docker-compose.yml` | Add Qdrant service |
| `start-dev.sh` | Start Qdrant container |
| `Dockerfile` | Add PyPDF2/pdfplumber to requirements |
| `requirements.txt` | Add qdrant-client, PyPDF2, openai (for embeddings) |
| `prompts/system.md` | Add memory awareness, domain routing instructions, creative behavior rules |
| `data/personas/mike/files/` (new dir) | Demo PDF/MD/image files |
