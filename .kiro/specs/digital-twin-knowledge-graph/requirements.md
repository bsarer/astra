# Requirements Document

## Introduction

AstraOS currently stores user context as flat vector embeddings in Qdrant (memories and file_index collections) with keyword-based domain routing. This works for simple retrieval but lacks structured relationships between entities, temporal awareness, and the ability to reason across connected data. The Digital Twin Knowledge Graph evolves the existing memory infrastructure into a structured, relationship-aware knowledge layer that models entities (people, companies, deals, files, events) with typed edges, supports time-aware retrieval, enables cross-domain graph traversal, and drives proactive intelligence based on the user's evolving context. This builds on top of the existing `memory.py`, `domain_router.py`, and `workflow_engine.py` without replacing them.

## Glossary

- **Knowledge_Graph**: A Qdrant-backed data structure that stores entities as points and relationships as payload metadata, enabling typed traversal between connected entities
- **Entity**: A discrete node in the Knowledge_Graph representing a person, company, deal, file, event, or concept, stored as a Qdrant point with an embedding and structured payload
- **Relationship**: A typed, directional edge between two Entities (e.g., works_at, has_deal, involves_file), stored as payload metadata on the source Entity point
- **Entity_Type**: The classification of an Entity — one of: person, company, deal, file, event, topic, location
- **Relationship_Type**: The classification of a Relationship edge — one of: works_at, has_deal, involves, attended_by, related_to, located_in, mentions, authored_by, scheduled_for, owns
- **Graph_Manager**: The Python module (`graph_manager.py`) that provides the API for creating, querying, and traversing the Knowledge_Graph, built on top of the existing MemoryManager
- **Entity_Extractor**: The component within Graph_Manager that parses conversations, emails, and files to identify Entities and Relationships using pattern matching and LLM extraction
- **Temporal_Score**: A numeric weight applied during retrieval that boosts Entities and Relationships relevant to the current time window (upcoming events score higher than past events)
- **Graph_Traversal**: The process of following Relationship edges from a starting Entity to discover connected Entities across domains
- **Relevance_Context**: The assembled set of Entities, Relationships, and memories retrieved via Graph_Traversal and injected into the agent system prompt before each LLM call
- **Proactive_Engine**: The component that monitors the Knowledge_Graph state and surfaces anticipatory suggestions (upcoming meetings with related files, approaching deadlines, stale context)
- **Preference_Model**: A set of weighted Entity interactions (views, dismissals, engagements) stored in the Knowledge_Graph that influence retrieval ranking over time
- **AstraOS**: The AI operating system application comprising the FastAPI backend, LangGraph agent, and Tauri/React frontend
- **MemoryManager**: The existing `memory.py` class that handles Qdrant storage and retrieval of memories and file indexes
- **DomainRouter**: The existing `domain_router.py` module that classifies text into knowledge domains (finance, sales, travel, team, personal, admin)

## Requirements

### Requirement 1: Entity Storage and Schema

**User Story:** As a developer, I want to store structured entities with typed relationships in Qdrant, so that the system can model real-world connections between people, companies, deals, files, and events.

#### Acceptance Criteria

1. THE Graph_Manager SHALL store each Entity as a Qdrant point in a `knowledge_graph` collection with payload fields: `entity_id`, `entity_type`, `name`, `properties` (dict), `relationships` (list of edge objects), `domains` (list), `created_at`, `updated_at`, `access_count`
2. THE Graph_Manager SHALL support Entity_Types: person, company, deal, file, event, topic, location
3. THE Graph_Manager SHALL store each Relationship as an object within the source Entity payload containing: `target_id`, `relationship_type`, `properties` (dict), `created_at`
4. THE Graph_Manager SHALL support Relationship_Types: works_at, has_deal, involves, attended_by, related_to, located_in, mentions, authored_by, scheduled_for, owns
5. WHEN an Entity with the same `name` and `entity_type` already exists, THE Graph_Manager SHALL merge the new properties and relationships into the existing Entity rather than creating a duplicate
6. THE Graph_Manager SHALL embed each Entity using the existing MemoryManager embedding pipeline (text-embedding-3-small, 1536 dimensions)
7. THE Graph_Manager SHALL tag each Entity with domains using the existing DomainRouter classification

### Requirement 2: Entity Extraction from Conversations

**User Story:** As a user, I want the system to automatically identify people, companies, deals, and events from my conversations, so that the knowledge graph stays current without manual input.

#### Acceptance Criteria

1. WHEN a user conversation turn completes, THE Entity_Extractor SHALL parse the user message and agent response to identify mentioned Entities
2. THE Entity_Extractor SHALL use pattern matching as a first pass to detect: person names (capitalized proper nouns matching known contacts), company names (matching known clients), deal references (dollar amounts with client names), file references (matching indexed filenames), and event references (dates, times, meeting mentions)
3. WHEN pattern matching yields ambiguous results, THE Entity_Extractor SHALL use a lightweight LLM call (gpt-4o with a structured output schema) to extract Entities and Relationships
4. WHEN a new Entity is extracted, THE Entity_Extractor SHALL check for existing Entities with the same name and type before creating a new one
5. WHEN a Relationship between two Entities is detected in conversation, THE Entity_Extractor SHALL create bidirectional Relationship edges on both Entity points
6. THE Entity_Extractor SHALL run asynchronously after each agent response without blocking the response stream
7. IF the Entity_Extractor encounters an error during extraction, THEN THE Entity_Extractor SHALL log the error and continue without affecting the agent response

### Requirement 3: Graph Traversal and Query

**User Story:** As a user, I want to ask about connections between entities (e.g., "what do I know about Tom Bradley and Acme?"), so that the system can traverse the knowledge graph and assemble a complete picture.

#### Acceptance Criteria

1. THE Graph_Manager SHALL provide a `traverse(entity_id, depth, relationship_types)` method that follows Relationship edges up to the specified depth and returns connected Entities
2. THE Graph_Manager SHALL provide a `query(text, entity_types, domains, limit)` method that combines semantic search with graph traversal to find relevant Entities
3. WHEN the agent receives a user query, THE Graph_Manager SHALL first perform semantic search to find seed Entities, then traverse one hop from each seed to discover connected Entities
4. THE Graph_Manager SHALL apply domain filtering from the DomainRouter during traversal to prevent irrelevant cross-domain results
5. THE Graph_Manager SHALL return traversal results as a structured list containing each Entity's name, type, properties, and the Relationship path that connected it to the query
6. WHEN traversal returns more than 10 Entities, THE Graph_Manager SHALL rank results by a combined score of semantic similarity, Temporal_Score, and access frequency, returning only the top 10

### Requirement 4: Temporal Context Awareness

**User Story:** As a user, I want the system to understand what is relevant right now versus historically, so that upcoming meetings and imminent deadlines are prioritized over past events.

#### Acceptance Criteria

1. THE Graph_Manager SHALL compute a Temporal_Score for each Entity based on associated timestamps: events within 60 minutes receive a score of 1.0, events within 24 hours receive 0.7, events within 7 days receive 0.4, and older events receive 0.1
2. WHEN retrieving Entities for context injection, THE Graph_Manager SHALL multiply the semantic similarity score by the Temporal_Score to produce the final ranking
3. THE Graph_Manager SHALL extract temporal metadata from event Entities including: `start_time`, `end_time`, `deadline`, and `reminder_time`
4. WHEN an event Entity has a `start_time` within 60 minutes of the current time, THE Graph_Manager SHALL flag the Entity as `urgent` in the retrieval results
5. THE Graph_Manager SHALL re-score temporal relevance at query time rather than at storage time, so that relevance changes as time passes

### Requirement 5: Cross-Domain Graph Reasoning

**User Story:** As a user, I want the system to connect dots across domains (e.g., a stock alert + advisor meeting + portfolio holdings form a coherent context), so that I get enriched insights without asking.

#### Acceptance Criteria

1. WHEN Graph_Traversal discovers Entities spanning multiple domains connected by Relationship edges, THE Graph_Manager SHALL include cross-domain Entities in the result set
2. THE Graph_Manager SHALL only bridge across domains when a concrete Relationship edge exists between the Entities (shared person, shared company, shared event)
3. WHEN cross-domain Entities are included, THE Graph_Manager SHALL annotate each Entity with the Relationship path that justified the cross-domain inclusion
4. THE Graph_Manager SHALL respect the existing DomainRouter BRIDGE_RULES to determine which domain pairs are eligible for cross-domain traversal
5. WHEN a query touches a single domain and no Relationship edges connect to other domains, THE Graph_Manager SHALL restrict results to the queried domain only
6. THE Graph_Manager SHALL limit cross-domain expansion to one additional domain beyond the primary query domain to prevent context explosion

### Requirement 6: Proactive Intelligence

**User Story:** As a user, I want the system to anticipate my needs based on the knowledge graph state (e.g., surface relevant files before a meeting, remind me of approaching deadlines), so that I spend less time searching for context.

#### Acceptance Criteria

1. THE Proactive_Engine SHALL run a periodic check (every 5 minutes) against the Knowledge_Graph to identify actionable context
2. WHEN an event Entity has a `start_time` within 30 minutes, THE Proactive_Engine SHALL traverse the event's Relationships to find connected person, company, deal, and file Entities and assemble a preparation summary
3. WHEN a file Entity is connected to an upcoming event Entity via Relationship edges, THE Proactive_Engine SHALL surface the file in the preparation summary without the user requesting it
4. WHEN a deal Entity has a `deadline` within 48 hours and the user has not queried that deal in the current session, THE Proactive_Engine SHALL generate a reminder notification
5. IF the user has dismissed a proactive suggestion for a specific Entity within the current session, THEN THE Proactive_Engine SHALL suppress further suggestions for that Entity until the next session
6. THE Proactive_Engine SHALL deliver suggestions by injecting a `[SYSTEM]` message into the agent conversation, triggering the existing agent processing pipeline

### Requirement 7: User Preference Learning

**User Story:** As a user, I want the system to learn from my interactions (what I engage with, dismiss, or ignore), so that future suggestions and context retrieval improve over time.

#### Acceptance Criteria

1. WHEN the user engages with a proactive suggestion (clicks, asks follow-up questions), THE Preference_Model SHALL increment the `access_count` on the related Entities and store an `engagement` episode in memory
2. WHEN the user dismisses a proactive suggestion, THE Preference_Model SHALL store a `dismissal` episode in memory tagged with the Entity and domain
3. THE Preference_Model SHALL compute a preference weight for each Entity_Type and domain combination based on the ratio of engagements to dismissals over the last 30 days
4. WHEN retrieving Entities for context injection, THE Graph_Manager SHALL apply the Preference_Model weights as a multiplier on the retrieval score
5. THE Preference_Model SHALL store preference data as memories of type `fact` with tag `preference_signal` in the existing MemoryManager, reusing the Qdrant `memories` collection
6. WHEN the Preference_Model has fewer than 5 interaction signals for a domain, THE Preference_Model SHALL use a neutral weight of 1.0 (no boosting or penalizing)

### Requirement 8: Knowledge Graph Context Injection into Agent

**User Story:** As a developer, I want the knowledge graph context to be injected into the agent's system prompt alongside existing memory context, so that the agent can reason over structured relationships.

#### Acceptance Criteria

1. WHEN the agent processes a user message, THE Graph_Manager SHALL be queried in parallel with the existing MemoryManager retrieval
2. THE Graph_Manager SHALL format traversal results as a `### Knowledge Graph Context:` section containing Entity names, types, key properties, and Relationship summaries
3. THE Graph_Manager SHALL limit the injected context to 400 tokens to stay within the existing 800-token retrieval budget (400 tokens for memories + 400 tokens for graph context)
4. WHEN both MemoryManager and Graph_Manager return results for the same Entity, THE agent context injection SHALL deduplicate by preferring the Graph_Manager result (which includes Relationship data)
5. IF the Graph_Manager query fails or times out (over 500ms), THEN THE agent SHALL proceed with only MemoryManager context without error
6. THE Graph_Manager context injection SHALL be added to the `chatbot_node` in `agent.py` alongside the existing domain-aware memory injection block

### Requirement 9: Seed Knowledge Graph for Demo Persona

**User Story:** As a developer, I want the knowledge graph pre-populated with Mike Astra's known entities and relationships, so that the demo shows immediate value without requiring conversation history.

#### Acceptance Criteria

1. WHEN AstraOS starts and the `knowledge_graph` collection is empty, THE Graph_Manager SHALL load seed Entities from a `data/personas/mike/knowledge_seed.json` file
2. THE seed data SHALL include Entities for: Mike Astra (person), Vertex Solutions (company), Acme Corp (company), BluePeak Industries (company), NovaTech (company), Tom Bradley (person), Rachel Kim (person), Dave Wilson (person), Sarah Chen (person), Jake Morrison (person), Priya Patel (person), Lisa Park (person), Helsinki Trip (event), Q1 Pipeline (deal), Acme Renewal (deal), BluePeak Expansion (deal), NovaTech New Business (deal)
3. THE seed data SHALL include Relationships: Mike works_at Vertex Solutions, Tom Bradley works_at Acme Corp, Acme Corp has_deal Acme Renewal ($450K), Acme Renewal involves Acme_Pricing_Tiers.md, Sarah Chen works_at Vertex Solutions, Jake Morrison works_at Vertex Solutions, Priya Patel works_at Vertex Solutions, Lisa Park works_at Vertex Solutions, Helsinki Trip located_in Helsinki, Q1 Pipeline involves Q1_Pipeline_Report.md, NovaTech New Business involves NovaTech_Demo_Notes.md, Board_Deck_Q1_Draft.md mentions Q1 Pipeline
4. THE Graph_Manager SHALL skip seeding if the `knowledge_graph` collection already contains Entities for the current persona
5. THE seed loading SHALL complete within 10 seconds for the demo dataset

### Requirement 10: Knowledge Graph Serialization and Round-Trip Integrity

**User Story:** As a developer, I want to serialize the knowledge graph to JSON and deserialize it back without data loss, so that seed data can be authored as files and graph state can be exported for debugging.

#### Acceptance Criteria

1. THE Graph_Manager SHALL provide a `serialize(entity_ids) -> str` method that exports specified Entities and their Relationships as a JSON string
2. THE Graph_Manager SHALL provide a `deserialize(json_str) -> list[Entity]` method that parses a JSON string into Entity objects and stores them in Qdrant
3. FOR ALL valid Knowledge_Graph states, serializing then deserializing then serializing again SHALL produce an identical JSON string (round-trip property)
4. THE serializer SHALL include all Entity fields: `entity_id`, `entity_type`, `name`, `properties`, `relationships`, `domains`, `created_at`, `updated_at`
5. IF the JSON input to `deserialize` contains invalid Entity_Types or Relationship_Types, THEN THE Graph_Manager SHALL return a descriptive error listing the invalid values
6. IF the JSON input to `deserialize` contains a Relationship referencing a `target_id` not present in the input or existing collection, THEN THE Graph_Manager SHALL store the Entity but log a warning about the dangling reference

