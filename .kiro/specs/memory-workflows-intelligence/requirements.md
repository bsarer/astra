# Requirements: Persistent Memory, Learned Workflows & Proactive Intelligence

## Problem Statement
Current AI assistants hit a "Phase 2 wall" — users spend more time maintaining context (prompts, memory, preferences) than the AI saves them. AstraOS solves this by making the OS itself maintain context through observation, persistent memory, and learned workflows. The user never updates a prompt or manages memory — the system does it automatically.

## User Story: Mike's Day with AstraOS

### Morning (Cold Start — The OS Already Knows)
Mike opens AstraOS at 8:15 AM. Without typing anything:
- The desktop populates with a **Morning Briefing** window: today's calendar (3 meetings), 4 unread emails, his Helsinki flight is tomorrow, NVDA is up 3.2% pre-market.
- A **Travel Prep** window appears: "Your flight to Helsinki is tomorrow at 4:30 PM. Here's your packing checklist, weather forecast (-2°C), and a PDF of your hotel confirmation."
- The agent noticed from memory that Mike always checks stocks first thing — it already has the watchlist summary rendered.
- A small notification: "I found a Q1 Pipeline Report PDF in your files that's relevant to your 10 AM meeting with Lisa. Want me to summarize it?"

### Mid-Morning (Cross-Source Correlation — The Creative Agent)
- A Bloomberg email arrives mentioning NVDA earnings beat. The agent auto-processes it (learned workflow from last week), renders a stock alert widget.
- But it goes further: it correlates that Mike has a meeting with his financial advisor next week (from calendar) and NVDA is in his holdings. It proactively creates a **Portfolio Briefing** widget combining the email insight + current positions + a suggested talking point for the advisor meeting.
- Mike didn't ask for any of this. The agent connected dots across email, calendar, stocks, and memory.

### Afternoon (Workflow Discovery — The OS Learns)
- Mike asks "prepare for my 2pm with Tom from Acme." The agent:
  - Pulls the calendar event (Acme Corp Renewal Call)
  - Searches memory: "Last interaction with Tom — he asked about volume discounts, onboarding timeline, and payment terms" (from email #2)
  - Finds a pricing PDF in Mike's files
  - Renders a **Meeting Prep** widget with all context combined
- After doing this twice for different meetings, the agent proposes: "I notice you always want meeting prep before calls. Want me to automatically prepare a briefing 30 minutes before each client meeting?"
- Mike clicks "Enable." Workflow created. No prompt engineering.

### Evening (Memory Persistence — It Remembers)
- Mike dismisses the stock alert widget. The agent remembers: "Mike dismissed TSLA alert — lower interest."
- Mike says "remind me to follow up with Rachel about BluePeak security review." The agent stores this in memory with a time trigger.
- Next morning, the reminder surfaces automatically.

## Functional Requirements

### FR-1: Qdrant Vector Memory Store
- FR-1.1: Qdrant runs as a Docker container alongside the backend
- FR-1.2: Every conversation turn extracts and stores facts (preferences, decisions, dismissed items, action patterns)
- FR-1.3: Before each agent response, retrieve top-K relevant memories via semantic search
- FR-1.4: Memory types: `fact` (user preference), `episode` (what happened), `workflow` (learned pattern), `reminder` (time-triggered), `file_summary` (indexed document)
- FR-1.5: Memory has decay — older, less-accessed memories rank lower
- FR-1.6: Agent can explicitly store/retrieve memories via tools

### FR-2: User File System (Mounted Directory)
- FR-2.1: Mount `data/personas/mike/files/` into the Docker container at `/app/data/personas/mike/files/`
- FR-2.2: Agent can list, read, and search files (PDF, images, text, markdown)
- FR-2.3: On startup, index all files into Qdrant with summaries
- FR-2.4: When files are relevant to current context (meeting, email, task), agent proactively surfaces them
- FR-2.5: Support PDF text extraction and image description
- FR-2.6: Files directory contains demo content:
  - `Q1_Pipeline_Report.pdf` — Sales pipeline data for Lisa's review
  - `Acme_Pricing_Tiers.pdf` — Tiered pricing for the Acme renewal
  - `Helsinki_Travel_Guide.pdf` — Travel tips and maps
  - `NovaTech_Product_Demo_Notes.md` — Jake's demo notes
  - `Team_Photo_Austin_Offsite.jpg` — Team photo from recent offsite
  - `Board_Deck_Q1_Draft.pdf` — Q1 board presentation draft

### FR-3: Morning Briefing (Proactive Intelligence)
- FR-3.1: On first connection each day, render a comprehensive briefing window
- FR-3.2: Briefing includes: calendar summary, unread email highlights, stock movers, upcoming travel alerts, time-sensitive reminders from memory
- FR-3.3: If a trip is within 48 hours, include weather, packing status, and relevant documents
- FR-3.4: If any files are relevant to today's meetings, mention them proactively
- FR-3.5: Briefing adapts based on learned preferences (e.g., Mike always checks stocks first → stocks section is prominent)

### FR-4: Learned Workflows (Pattern Discovery)
- FR-4.1: Track action sequences in memory (e.g., "email_arrived → stock_analysis → widget_rendered")
- FR-4.2: After detecting a pattern 2+ times, propose automation to the user
- FR-4.3: Workflow proposal renders as an interactive widget with Enable/Dismiss buttons
- FR-4.4: Enabled workflows are stored in Qdrant with type `workflow`
- FR-4.5: On trigger events (new email, calendar change, time-of-day), check if any workflow matches and execute automatically
- FR-4.6: Workflow management widget: list active workflows, toggle on/off, delete
- FR-4.7: Built-in seed workflows for demo:
  - "Bloomberg email → stock analysis → alert widget" (auto-enabled after 2nd trigger)
  - "Meeting in 30 min → prep briefing with attendee history + relevant files"
  - "Morning login → full briefing"

### FR-5: Creative Agent Behaviors (Cross-Source Correlation)
- FR-5.1: Agent correlates data across sources (email + calendar + stocks + files + memory) without being asked
- FR-5.2: When rendering a widget, agent checks if related context exists in other sources and enriches the output
- FR-5.3: Examples of creative correlations:
  - Email mentions a client + calendar has meeting with that client → combine into prep widget
  - Stock alert + upcoming advisor meeting → portfolio briefing with talking points
  - Travel email + weather data + file (travel guide PDF) → enriched travel widget
  - SDR report mentions new leads + no follow-up calendar events → suggest scheduling
- FR-5.4: Agent suggests actions the user hasn't thought of: "You have a meeting with Rachel about security concerns. I found a case study PDF in your files that addresses similar concerns — want me to attach it to a prep email?"
- FR-5.5: Track which creative suggestions the user accepts/dismisses to improve future suggestions

### FR-6: Memory Tools for the Agent
- FR-6.1: `store_memory(content, memory_type, tags)` — explicitly store a fact, episode, or reminder
- FR-6.2: `search_memory(query, memory_type, limit)` — semantic search across stored memories
- FR-6.3: `list_workflows()` — list all learned/enabled workflows
- FR-6.4: `enable_workflow(workflow_id)` / `disable_workflow(workflow_id)` — toggle workflows
- FR-6.5: `list_files(directory)` — list files in the user's mounted directory
- FR-6.6: `read_file(path)` — read content of a file (text, PDF extraction, image description)
- FR-6.7: `search_files(query)` — semantic search across indexed file summaries

### FR-7: Domain-Aware Context Routing
The system must be smart about WHAT context it retrieves for a given situation. Not everything is relevant to everything. Dumping all memories/files/emails into the prompt is the Phase 1 mistake — AstraOS should route context by domain.

- FR-7.1: **Domain Classification** — Every piece of stored content (memory, file, email, calendar event) gets tagged with one or more domains at ingestion time:
  - `finance` — stock alerts, portfolio, market news, financial advisor meetings
  - `sales` — client deals, pipeline, CRM, pricing, renewals
  - `travel` — trips, flights, hotels, weather, packing, itineraries
  - `team` — 1:1s, SDR reports, team metrics, internal comms
  - `personal` — hobbies, interests, non-work items
  - `admin` — reminders, scheduling, general tasks

- FR-7.2: **Query Domain Detection** — When the user asks something or an event triggers, the system classifies the intent domain BEFORE retrieving context:
  - "Bloomberg email about NVDA" → domain: `finance` → retrieve only financial memories, stock history, advisor meetings. Do NOT pull travel context or team 1:1 notes.
  - "Prepare for my meeting with Tom" → domain: `sales` → retrieve Acme deal history, pricing files, Tom's past emails. Do NOT pull stock data or travel info.
  - "What's the weather in Helsinki?" → domain: `travel` → retrieve trip details, packing list, travel guide PDF. Do NOT pull sales pipeline or stock alerts.

- FR-7.3: **Contextual Relevance Scoring** — When retrieving from Qdrant, apply a two-stage filter:
  1. **Domain filter**: Only retrieve memories/files matching the detected domain(s)
  2. **Semantic similarity**: Within the filtered set, rank by embedding similarity to the query
  - This prevents the "kitchen sink" problem where irrelevant context dilutes the useful stuff

- FR-7.4: **Cross-Domain Bridging** — Some situations legitimately span domains. The system should detect these and pull from multiple domains, but only when there's a real connection:
  - Email about NVDA + calendar shows financial advisor meeting → bridge `finance` + `sales` (advisor context)
  - Client meeting + pricing PDF in files → bridge `sales` + `files`
  - Trip tomorrow + weather + packing list → bridge `travel` + `personal`
  - But: stock alert should NEVER pull in travel packing tips. Meeting prep should NEVER include unrelated stock data.

- FR-7.5: **Domain-Aware File Indexing** — When files are indexed at startup, each file gets domain tags based on content:
  - `Q1_Pipeline_Report.pdf` → `sales`, `team`
  - `Acme_Pricing_Tiers.pdf` → `sales`
  - `Helsinki_Travel_Guide.pdf` → `travel`
  - `NovaTech_Product_Demo_Notes.md` → `sales`
  - `Board_Deck_Q1_Draft.pdf` → `sales`, `team`
  - `Team_Photo_Austin_Offsite.jpg` → `team`, `personal`

- FR-7.6: **Email Domain Classification** — Emails are classified at fetch time:
  - Bloomberg/market emails → `finance`
  - Client emails (Acme, BluePeak, NovaTech) → `sales`
  - Internal team emails (Sarah, Jake, Priya, Lisa) → `team`
  - Travel confirmations (Finnair, Hotel Kämp, tours) → `travel`
  - Classification uses sender, subject keywords, and body content

- FR-7.7: **Memory Domain Inheritance** — When the agent stores a memory from a conversation, it inherits the domain of that conversation's context:
  - User dismissed a stock alert → memory tagged `finance`
  - User asked about Acme pricing → memory tagged `sales`
  - User said "remind me to pack camera" → memory tagged `travel`

- FR-7.8: **Retrieval Budget** — The system has a context budget (e.g., top-5 memories, top-2 files, top-3 emails). Domain routing ensures this budget is spent on the RIGHT items, not wasted on irrelevant cross-domain noise. The agent should never inject more than ~800 tokens of retrieved context per turn.

## Non-Functional Requirements
- NFR-1: Qdrant container must start alongside the backend via docker-compose or start-dev.sh
- NFR-2: Memory retrieval must add < 500ms to response time (top-5 retrieval)
- NFR-3: File indexing happens at startup and should complete within 10s for < 50 files
- NFR-4: All memory operations are per-persona (keyed by user/persona ID)
- NFR-5: Workflow proposals should feel natural, not robotic — conversational tone
- NFR-6: Domain classification should be lightweight — keyword/rule-based first pass, embedding-based second pass only when ambiguous
- NFR-7: Context retrieval should feel invisible to the user — they should never see irrelevant context bleed into responses
