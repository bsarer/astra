# Tasks: Persistent Memory, Learned Workflows & Proactive Intelligence

## Task 1: Qdrant Infrastructure Setup
- [x] Add Qdrant URL config to `docker-compose.yml` (uses `QDRANT_URL=http://host.docker.internal:6333`)
- [ ] Add Qdrant as a service in docker-compose (optional — can run standalone)
- [x] Add `qdrant-client` and `openai` to `requirements.txt`
- [x] Rebuild Docker image with new dependencies
- [x] Graceful fallback: in-process memory store when Qdrant unavailable

**Depends on:** Nothing
**Validates:** FR-1.1, NFR-1

## Task 2: Domain Router (`domain_router.py`)
- [x] Create `PoC/astra-poc-vc/domain_router.py`
- [x] Implement `DOMAINS` taxonomy with keywords, senders, file_patterns for: finance, sales, travel, team, personal, admin
- [x] Implement `classify(text, sender=None) -> list[str]` — keyword scoring with 3x threshold for single-domain confidence
- [x] Implement sender-based classification for emails
- [x] Implement cross-domain bridging logic: only bridge when entity/temporal overlap exists
- [x] Add unit-testable examples: "Bloomberg NVDA email" → `["finance"]`, "Acme renewal prep" → `["sales"]`, "Helsinki weather" → `["travel"]`

**Depends on:** Nothing
**Validates:** FR-7.1, FR-7.2, FR-7.3, FR-7.4, NFR-6

## Task 3: Memory Manager (`memory.py`)
- [x] Create `PoC/astra-poc-vc/memory.py`
- [x] Implement `MemoryManager.__init__` — connect to Qdrant, create collections if not exist (memories, file_index)
- [x] Implement `embed(text) -> list[float]` using OpenAI text-embedding-3-small
- [x] Implement `store(content, memory_type, tags, domains)` — embed + upsert to Qdrant with payload
- [x] Implement `retrieve(query, domains, memory_type, limit)` — domain-filtered semantic search
- [x] Implement `extract_facts(user_message, agent_response)` — rule-based extraction in agent.py
- [x] Add singleton `get_memory_manager()` for use across modules

**Depends on:** Task 1, Task 2
**Validates:** FR-1.2, FR-1.3, FR-1.4, FR-1.5, FR-1.6, FR-7.3, FR-7.8, NFR-2

## Task 4: Demo Files + File Indexing
- [x] Create `data/personas/mike/files/` directory
- [x] Create demo files:
  - `Q1_Pipeline_Report.md` (markdown version of pipeline data — Acme $450K, BluePeak $280K, NovaTech $180K)
  - `Acme_Pricing_Tiers.md` (pricing table with volume discounts and onboarding timeline)
  - `Helsinki_Travel_Guide.md` (restaurants, sauna etiquette, transport, Finnish phrases, photo spots)
  - `NovaTech_Demo_Notes.md` (Jake's demo notes — API integration, Dave Wilson, close by March)
  - `Board_Deck_Q1_Draft.md` (Q1 board deck — 87% of target, 3 deals, BluePeak risk)
- [x] Note: Using .md instead of .pdf for PoC simplicity — avoids PDF generation/parsing complexity
- [x] Docker volume mounts files directory via `data/` volume
- [x] Implement file indexing in `tools_files.py`: `index_all_files()` — walk dir, read content, classify domains, embed summaries, store in Qdrant `file_index` collection
- [x] Call `index_all_files()` at startup in `main.py` lifespan

**Depends on:** Task 3
**Validates:** FR-2.1, FR-2.2, FR-2.3, FR-2.5, FR-2.6, FR-7.5, NFR-3

## Task 5: File System Tools (`tools_files.py`)
- [x] Create `PoC/astra-poc-vc/tools_files.py`
- [x] Implement `list_user_files(directory?)` tool — returns filenames, types, sizes, domain tags
- [x] Implement `read_user_file(path)` tool — reads file content (markdown/text directly)
- [x] Implement `search_user_files(query)` tool — semantic search against Qdrant `file_index` collection, domain-filtered via DomainRouter
- [x] Register tools in `agent.py`

**Depends on:** Task 3, Task 4
**Validates:** FR-2.2, FR-2.4, FR-6.5, FR-6.6, FR-6.7

## Task 6: Memory Tools (`tools_memory.py`)
- [x] Create `PoC/astra-poc-vc/tools_memory.py`
- [x] Implement `store_memory(content, memory_type, tags)` tool — stores via MemoryManager with auto-domain classification
- [x] Implement `search_memory(query, memory_type?, limit?)` tool — domain-aware semantic search
- [x] Implement `list_workflows()` tool — returns all workflows with status
- [x] Implement `enable_workflow(workflow_id)` / `disable_workflow(workflow_id)` tools
- [x] Register tools in `agent.py`

**Depends on:** Task 3
**Validates:** FR-6.1, FR-6.2, FR-6.3, FR-6.4

## Task 7: Integrate Memory into Agent (`agent.py`)
- [x] Import MemoryManager and DomainRouter
- [x] In `chatbot_node`: before LLM call, classify user message domain → retrieve relevant memories + files → inject as context section in system prompt
- [x] Context injection format: `### Relevant Memory:` + `### Relevant Files:` sections
- [x] After agent response: `memory_extract_node` extracts and stores new memories
- [x] After agent response: log action sequence (tool calls made) for workflow detection via `engine.log_action()`
- [x] Add all new tools (file tools + memory tools) to the tools list

**Depends on:** Task 5, Task 6
**Validates:** FR-1.3, FR-7.2, FR-7.3, FR-7.8

## Task 8: Workflow Engine
- [x] Add workflow pattern detection to `workflow_engine.py`: `detect_workflow_pattern(trigger, actions)` — checks if trigger+actions combo seen 2+ times
- [x] Add seed workflows at startup (in-memory, persisted during session):
  - `bloomberg_stock_alert` (hit_count=1, enabled=false)
  - `meeting_prep` (hit_count=0, enabled=false)
  - `morning_briefing` (hit_count=0, enabled=true)
- [x] In `agent.py` post-response hook: log trigger+actions, call detect_workflow_pattern
- [x] When pattern detected (2+ hits): agent emits a workflow proposal widget via `emit_ui` with Enable/Dismiss buttons
- [x] Handle Enable/Dismiss button actions in `main.py`: workflow_enable/workflow_dismiss handlers
- [x] In email poller (`main.py`): before processing email, check if `bloomberg_stock_alert` workflow is enabled → auto-execute with context
- [x] Email polling now 2 min default (configurable via `EMAIL_POLL_INTERVAL` env var)
- [x] Stock emails pull relevant files/memories for finance domain context

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
