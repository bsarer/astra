# Tasks: Persistent Memory, Learned Workflows & Proactive Intelligence

## Task 1: Qdrant Infrastructure Setup
- [ ] Add Qdrant service to `docker-compose.yml` (port 6333, persistent volume)
- [ ] Update `start-dev.sh` to start Qdrant container before backend
- [ ] Add `qdrant-client` and `openai` to `requirements.txt`
- [ ] Rebuild Docker image with new dependencies
- [ ] Verify Qdrant is accessible from backend container at `http://qdrant:6333` (compose) or `http://localhost:6333` (dev)

**Depends on:** Nothing
**Validates:** FR-1.1, NFR-1

## Task 2: Domain Router (`domain_router.py`)
- [ ] Create `PoC/astra-poc-vc/domain_router.py`
- [ ] Implement `DOMAINS` taxonomy with keywords, senders, file_patterns for: finance, sales, travel, team, personal, admin
- [ ] Implement `classify(text, sender=None) -> list[str]` — keyword scoring with 3x threshold for single-domain confidence
- [ ] Implement sender-based classification for emails
- [ ] Implement cross-domain bridging logic: only bridge when entity/temporal overlap exists
- [ ] Add unit-testable examples: "Bloomberg NVDA email" → `["finance"]`, "Acme renewal prep" → `["sales"]`, "Helsinki weather" → `["travel"]`

**Depends on:** Nothing
**Validates:** FR-7.1, FR-7.2, FR-7.3, FR-7.4, NFR-6

## Task 3: Memory Manager (`memory.py`)
- [ ] Create `PoC/astra-poc-vc/memory.py`
- [ ] Implement `MemoryManager.__init__` — connect to Qdrant, create collections if not exist (memories, files, workflows)
- [ ] Implement `embed(text) -> list[float]` using OpenAI text-embedding-3-small
- [ ] Implement `store(content, memory_type, tags, domains)` — embed + upsert to Qdrant with payload
- [ ] Implement `retrieve(query, domains, memory_type, limit)` — domain-filtered semantic search with decay scoring
- [ ] Implement memory decay: `score = similarity * recency_weight * access_bonus`
- [ ] Implement `extract_facts(user_message, agent_response)` — rule-based extraction of preferences, dismissals, reminders
- [ ] Add singleton `get_memory_manager()` for use across modules

**Depends on:** Task 1, Task 2
**Validates:** FR-1.2, FR-1.3, FR-1.4, FR-1.5, FR-1.6, FR-7.3, FR-7.8, NFR-2

## Task 4: Demo Files + File Indexing
- [ ] Create `data/personas/mike/files/` directory
- [ ] Create demo files:
  - `Q1_Pipeline_Report.md` (markdown version of pipeline data — Acme $450K, BluePeak $280K, NovaTech $180K)
  - `Acme_Pricing_Tiers.md` (pricing table with volume discounts and onboarding timeline)
  - `Helsinki_Travel_Guide.md` (restaurants, sauna etiquette, transport, Finnish phrases, photo spots)
  - `NovaTech_Product_Demo_Notes.md` (Jake's demo notes — API integration, Dave Wilson, close by March)
  - `Board_Deck_Q1_Draft.md` (Q1 board deck — 87% of target, 3 deals, BluePeak risk)
  - `Team_Photo_Austin_Offsite.txt` (placeholder description of team photo)
- [ ] Note: Using .md instead of .pdf for PoC simplicity — avoids PDF generation/parsing complexity. Can upgrade to real PDFs later.
- [ ] Update Docker volume mount in `start-dev.sh` to include files directory (already mounted via `data/` volume)
- [ ] Implement file indexing in `memory.py`: `index_files(directory)` — walk dir, read content, classify domains, embed summaries, store in Qdrant `files` collection
- [ ] Call `index_files()` at startup in `main.py` lifespan

**Depends on:** Task 3
**Validates:** FR-2.1, FR-2.2, FR-2.3, FR-2.5, FR-2.6, FR-7.5, NFR-3

## Task 5: File System Tools (`tools_files.py`)
- [ ] Create `PoC/astra-poc-vc/tools_files.py`
- [ ] Implement `list_user_files(directory?)` tool — returns filenames, types, sizes, domain tags
- [ ] Implement `read_user_file(path)` tool — reads file content (markdown/text directly)
- [ ] Implement `search_user_files(query)` tool — semantic search against Qdrant `files` collection, domain-filtered via DomainRouter
- [ ] Register tools in `agent.py`

**Depends on:** Task 3, Task 4
**Validates:** FR-2.2, FR-2.4, FR-6.5, FR-6.6, FR-6.7

## Task 6: Memory Tools (`tools_memory.py`)
- [ ] Create `PoC/astra-poc-vc/tools_memory.py`
- [ ] Implement `store_memory(content, memory_type, tags)` tool — stores via MemoryManager with auto-domain classification
- [ ] Implement `search_memory(query, memory_type?, limit?)` tool — domain-aware semantic search
- [ ] Implement `list_workflows()` tool — returns all workflows with status
- [ ] Implement `enable_workflow(workflow_id)` / `disable_workflow(workflow_id)` tools
- [ ] Register tools in `agent.py`

**Depends on:** Task 3
**Validates:** FR-6.1, FR-6.2, FR-6.3, FR-6.4

## Task 7: Integrate Memory into Agent (`agent.py`)
- [ ] Import MemoryManager and DomainRouter
- [ ] In `chatbot_node`: before LLM call, classify user message domain → retrieve relevant memories + files → inject as context section in system prompt
- [ ] Context injection format: `### Retrieved Context (domain: {domain}):\n{memories}\n{files}`
- [ ] Cap injected context at ~800 tokens
- [ ] After agent response: call `extract_facts()` to store new memories
- [ ] After agent response: log action sequence (tool calls made) for workflow detection
- [ ] Add all new tools (file tools + memory tools) to the tools list

**Depends on:** Task 5, Task 6
**Validates:** FR-1.3, FR-7.2, FR-7.3, FR-7.8

## Task 8: Workflow Engine
- [ ] Add workflow pattern detection to `memory.py`: `detect_workflow_pattern(trigger, actions)` — checks if trigger+actions combo seen 2+ times
- [ ] Add seed workflows to Qdrant at startup:
  - `bloomberg_stock_alert` (hit_count=1, enabled=false)
  - `meeting_prep` (hit_count=0, enabled=false)
  - `morning_briefing` (hit_count=0, enabled=true)
- [ ] In `agent.py` post-response hook: log trigger+actions, call detect_workflow_pattern
- [ ] When pattern detected (2+ hits): agent emits a workflow proposal widget via `emit_ui` with Enable/Dismiss buttons
- [ ] Handle Enable/Dismiss button actions: update workflow in Qdrant
- [ ] In email poller (`main.py`): before processing email, check if any enabled workflow matches the trigger → execute automatically

**Depends on:** Task 7
**Validates:** FR-4.1, FR-4.2, FR-4.3, FR-4.4, FR-4.5, FR-4.6, FR-4.7

## Task 9: Enhanced Morning Briefing
- [ ] Update the proactive session start in `main.py` to use domain-routed context:
  - Pull `team` memories for meeting context
  - Pull `finance` memories for stock preferences
  - Pull `travel` memories/files for upcoming trips
- [ ] Include file awareness: "I found [filename] relevant to your [meeting/task]"
- [ ] Include drift detection: surface things the user hasn't looked at (trip in 2 days, board deck due)
- [ ] Include time-sensitive reminders from memory
- [ ] Update `prompts/system.md` with morning briefing instructions that reference memory and files

**Depends on:** Task 7, Task 8
**Validates:** FR-3.1, FR-3.2, FR-3.3, FR-3.4, FR-3.5

## Task 10: Creative Agent Behaviors + System Prompt Updates
- [ ] Update `prompts/system.md` with:
  - Domain-aware context routing instructions (don't mix irrelevant domains)
  - Cross-source correlation rules (only bridge when entity/temporal link exists)
  - Creative suggestion guidelines (file surfacing, next-step suggestions, drift detection)
  - Memory awareness instructions (check what's stored, avoid re-processing)
- [ ] Add examples of good vs bad context routing:
  - GOOD: Stock email → pull financial memories + advisor calendar
  - BAD: Stock email → pull travel packing list
  - GOOD: Meeting prep → pull client emails + pricing PDF
  - BAD: Meeting prep → pull unrelated stock data
- [ ] Add creative behavior triggers:
  - After meeting prep → suggest follow-up email draft
  - After stock alert → check for advisor meeting → suggest portfolio briefing
  - After travel query → check weather + files → enrich with guide content
- [ ] Track accepted/dismissed suggestions in memory for future improvement

**Depends on:** Task 7
**Validates:** FR-5.1, FR-5.2, FR-5.3, FR-5.4, FR-5.5, FR-7.2, NFR-7
