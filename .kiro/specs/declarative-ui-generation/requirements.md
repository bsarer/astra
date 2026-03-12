# Requirements Document

## Introduction

This feature migrates the Astra Agent's UI generation pipeline from a Python-side renderer with vanilla JS frontend to a modern React + CopilotKit + AG-UI architecture inside Tauri. The core principle remains: the agent decides WHAT to show (emitting declarative A2UI JSON), and the frontend decides HOW to render it (React components styled with the AIOS design system).

The abandoned approach used a Python-side `AIOSRenderer` that converted A2UI messages to HTML strings, delivered via WebSocket to iframes in a GridStack layout. The new approach eliminates server-side rendering entirely:

- **Agent Layer** — The LangGraph agent emits A2UI JSON messages (`surfaceUpdate`, `beginRendering`, `deleteSurface`) via the `emit_ui` tool. The A2UI adjacency list component model is retained.
- **Transport Layer** — The `ag-ui-langgraph` Python package wraps the existing LangGraph agent and exposes it as an AG-UI compatible SSE endpoint, replacing the custom WebSocket transport.
- **Frontend Layer** — A React app inside Tauri uses CopilotKit's `useAgent` hook and A2UI renderer to receive agent events and render custom AIOS-themed React components. No iframes, no GridStack, no server-side HTML generation.

This cleanly separates agent context (tools, persona, domain intelligence) from UI context (React components, styling), reduces backend complexity (no renderer module), and enables a richer, more interactive frontend.

## Glossary

- **A2UI**: Agent-to-User Interface — a declarative UI protocol where AI agents emit structured JSON component descriptions instead of executable code. Components use an adjacency list model with ID references.
- **AG-UI**: Agent-User Interaction Protocol — CopilotKit's open-source event-driven streaming protocol that transports agent events (text tokens, tool calls, state patches, A2UI messages, lifecycle signals) between backend and frontend via Server-Sent Events (SSE).
- **ag-ui-langgraph**: A Python PyPI package that wraps a LangGraph agent and exposes it as an AG-UI compatible SSE endpoint, handling protocol translation automatically.
- **CopilotKit**: A React framework for building AI-powered UIs. Provides hooks (`useAgent`, `useAGUI`), an A2UI renderer, and component mapping infrastructure for rendering agent-emitted UI.
- **surfaceUpdate**: An A2UI message type that defines or updates UI components on a named surface. Contains a `surfaceId` and a flat list of components using the adjacency list model.
- **beginRendering**: An A2UI message type that signals the frontend to render a surface, specifying the root component ID.
- **deleteSurface**: An A2UI message type that removes a previously rendered surface from the frontend.
- **Adjacency_List_Model**: A2UI's flat component representation where components are stored as a list with ID references (not nested trees). Each component has an `id`, a `type`, `props`, and references children by ID. This format is LLM-friendly — easy to generate incrementally.
- **Component_Map**: A registry that maps A2UI component type names (e.g., `"Card"`, `"StockTicker"`) to React component implementations. CopilotKit uses this map to resolve and render components.
- **AIOS_Design_System**: The visual design language for Astra — glassmorphic cards, CSS custom properties (`--bg-panel`, `--bg-card`, `--accent-blue`, etc.), Inter font, hover states, transitions. Applied via React component styling.
- **Astra_Agent**: The LangGraph-based AI agent (`agent.py`) that processes user requests, invokes tools, and emits A2UI JSON messages via the `emit_ui` tool.
- **SSE_Endpoint**: A FastAPI Server-Sent Events endpoint that streams AG-UI protocol events from the backend to the React frontend, replacing the previous WebSocket endpoint.
- **React_App**: The new React application scaffolded inside `tauri-app/`, served on port 7100, replacing the vanilla JS `static/app.js` + `static/index.html`.
- **Event_Bridge**: The mechanism by which interactive React components (buttons, clickable items) send user actions back to the Astra_Agent through CopilotKit's agent communication channel.

## Requirements

### Requirement 1: A2UI Message Protocol (Retained)

**User Story:** As a developer, I want the system to use the A2UI JSONL message protocol, so that agent-to-UI communication follows a well-defined declarative format.

#### Acceptance Criteria

1. THE system SHALL support the `surfaceUpdate` message type containing a `surfaceId` (string) and a `components` array using the adjacency list model, where each component has an `id` (string), a `type` (string), `props` (dict), and `children` (list of string IDs).
2. THE system SHALL support the `beginRendering` message type containing a `surfaceId` (string) and a `root` (string) identifying the root component ID to render.
3. THE system SHALL support the `deleteSurface` message type containing a `surfaceId` (string) to remove a previously rendered surface.
4. WHEN the Astra_Agent needs to display UI, it SHALL emit A2UI JSON messages via the `emit_ui` tool: first `surfaceUpdate` (defining components), then `beginRendering` (triggering render).
5. THE `surfaceId` SHALL uniquely identify a rendered surface in the React_App — each unique `surfaceId` corresponds to one rendered section in the dashboard layout.

### Requirement 2: Adjacency List Component Model (Retained)

**User Story:** As a developer, I want components to use A2UI's flat adjacency list model, so that the LLM can generate UI incrementally and components can be updated individually by ID.

#### Acceptance Criteria

1. THE `surfaceUpdate.components` array SHALL be a flat list where each entry contains an `id` (string), a `type` (string), `props` (dict), and `children` (list of string IDs), with no nested component trees.
2. Layout components (Row, Column, Card, Tabs) SHALL reference child components by ID in their `children` list, not by embedding child definitions inline.
3. EACH component `id` SHALL be a descriptive string (e.g., `"stock-alert-banner"`, `"email-list-row-3"`) rather than opaque numeric identifiers.
4. THE adjacency list model SHALL support incremental generation — the agent MAY emit components across multiple `surfaceUpdate` messages for the same `surfaceId` before calling `beginRendering`.

### Requirement 3: AG-UI SSE Transport

**User Story:** As a developer, I want the backend to expose an AG-UI compatible SSE endpoint using `ag-ui-langgraph`, so that the React frontend can connect via CopilotKit's standard agent protocol.

#### Acceptance Criteria

1. THE backend SHALL use the `ag-ui-langgraph` Python package to wrap the existing LangGraph agent and expose it as an AG-UI compatible SSE endpoint.
2. THE SSE_Endpoint SHALL stream AG-UI protocol events including text message tokens, tool call events, A2UI messages, and lifecycle signals (run started, run finished).
3. THE SSE_Endpoint SHALL be a FastAPI route (e.g., `POST /api/copilotkit`) that accepts AG-UI protocol requests and returns an SSE stream.
4. WHEN the Astra_Agent emits an `emit_ui` tool call, THE AG-UI transport SHALL include the A2UI JSON payload in the streamed events so that CopilotKit can process it on the frontend.
5. THE SSE_Endpoint SHALL support session management so that conversation history is maintained across requests for the same user session.
6. IF the SSE stream encounters an error during agent execution, THEN THE SSE_Endpoint SHALL emit an AG-UI error event with a descriptive message.

### Requirement 4: CopilotKit React Frontend

**User Story:** As a developer, I want a React frontend using CopilotKit that renders agent-emitted A2UI components as AIOS-themed React components, so that the UI is dynamic, interactive, and visually consistent.

#### Acceptance Criteria

1. THE React_App SHALL use CopilotKit's provider (`<CopilotKit>`) configured to connect to the backend SSE_Endpoint.
2. THE React_App SHALL use CopilotKit's `useAgent` (or `useAGUI`) hook to establish a connection with the Astra_Agent and receive streamed events.
3. THE React_App SHALL use CopilotKit's A2UI renderer to process `surfaceUpdate` and `beginRendering` messages and render the corresponding React components.
4. THE React_App SHALL register a Component_Map that maps A2UI type names to custom AIOS-themed React components (e.g., `"Card"` → `<AIOSCard/>`, `"StockTicker"` → `<AIOSStockTicker/>`).
5. WHEN a `deleteSurface` message is received, THE React_App SHALL remove the corresponding rendered surface from the display.
6. THE React_App SHALL display a chat interface alongside the rendered surfaces, showing streamed text tokens from the agent progressively.
7. THE React_App SHALL be served on port 7100 (matching the existing Tauri `devUrl` configuration) and be compatible with the Tauri desktop shell.

### Requirement 5: AIOS-Themed React Components

**User Story:** As a developer, I want custom React components styled with the AIOS design system, so that agent-generated UIs match the existing glassmorphic visual identity.

#### Acceptance Criteria

1. THE React_App SHALL include AIOS-themed React components for the following A2UI standard catalog types: `Text`, `Button`, `Card`, `Row`, `Column`, `Image`, `Icon`, `Divider`, `Tabs`, `List`.
2. THE React_App SHALL include AIOS-themed React components for the following custom Astra types: `StockTicker`, `StockAlert`, `EmailRow`, `MetricCard`, `SparklineChart`, `CalendarEvent`.
3. ALL AIOS-themed React components SHALL use the AIOS design system CSS custom properties (`--bg-panel`, `--bg-card`, `--accent-blue`, `--text-primary`, etc.), glassmorphic styling (backdrop-filter, translucent backgrounds), and the Inter font family.
4. WHEN a `surfaceUpdate` contains an unrecognized component type, THE React_App SHALL fall back to rendering a generic Card displaying the raw component data as formatted JSON.
5. THE `Button` React component SHALL emit user actions back to the Astra_Agent through CopilotKit's Event_Bridge when clicked, passing the `action` and `payload` props.
6. THE `Tabs` React component SHALL manage tab switching state locally and emit a `tab_changed` event back to the Astra_Agent when the active tab changes.

### Requirement 6: Astra Agent A2UI Output (Updated)

**User Story:** As a developer, I want the Astra_Agent to emit A2UI JSON messages via the `emit_ui` tool, so that the agent produces declarative UI without HTML/CSS knowledge.

#### Acceptance Criteria

1. THE Astra_Agent SHALL use the `emit_ui` tool that accepts a `surface_id`, a `components` list (A2UI adjacency list format), and optional `grid` hints as its arguments.
2. THE Astra_Agent system prompt SHALL NOT include widget template HTML, CSS design system rules, or rendering instructions.
3. THE Astra_Agent system prompt SHALL include: the A2UI adjacency list format specification, the component catalog (standard + custom types with props schemas), and instructions to emit A2UI messages via the `emit_ui` tool.
4. WHEN the Astra_Agent needs to display a stock alert, it SHALL emit a `surfaceUpdate` with components like `Card`, `Text`, `StockTicker`, `Button` in adjacency list format, followed by a `beginRendering` message.
5. WHEN the Astra_Agent needs to display the proactive dashboard, it SHALL emit a `surfaceUpdate` with a root layout component containing child components (via ID references) for trip alert, schedule, inbox summary, and stock alerts — composed from standard and custom catalog components.

### Requirement 7: Context Separation

**User Story:** As a developer, I want agent context and UI context to be cleanly separated, so that each can evolve independently and token usage is reduced.

#### Acceptance Criteria

1. THE Agent_Context (system prompt) SHALL contain only: system instructions, persona context, tool definitions (including `emit_ui`), A2UI format specification, component catalog (types and props schemas), and domain-specific intelligence (email, calendar, stock, travel).
2. THE UI_Context (React components + CSS) SHALL contain only: component implementations, AIOS design system styling, layout logic, and interaction wiring.
3. THE Agent_Context SHALL NOT contain any HTML tags, CSS properties, or JavaScript code.
4. THE UI_Context SHALL NOT contain any persona information, tool definitions, or domain-specific business logic.
5. WHEN a new custom component type is added, THE Component_Map SHALL be updated in the React_App (new React component) and the agent prompt (type name + props schema) — but the React component change SHALL NOT require modifying agent logic, and vice versa.

### Requirement 8: Backend AG-UI Integration

**User Story:** As a developer, I want the backend to integrate `ag-ui-langgraph` with the existing LangGraph agent, so that the agent is accessible via the AG-UI protocol with minimal changes to agent logic.

#### Acceptance Criteria

1. THE backend SHALL install `ag-ui-langgraph` as a Python dependency and use it to create an AG-UI adapter for the existing LangGraph compiled graph.
2. THE FastAPI application SHALL expose a new route (e.g., `POST /api/copilotkit`) that delegates to the `ag-ui-langgraph` adapter for handling AG-UI protocol requests.
3. THE `emit_ui` tool SHALL remain a passthrough tool in the LangGraph agent — it returns a confirmation string to the agent, and the AG-UI transport carries the tool call arguments (A2UI JSON) to the frontend.
4. THE existing `render_widget` tool SHALL be retained during migration for backward compatibility, but the agent prompt SHALL instruct the agent to prefer `emit_ui`.
5. THE backend SHALL continue to support the existing WebSocket endpoint (`/ws`) during the migration period so that the vanilla JS frontend remains functional until fully replaced.
6. WHEN the email poller detects new stock-related emails, THE backend SHALL trigger the Astra_Agent which emits A2UI messages, and the AG-UI transport SHALL deliver them to connected React frontends.

### Requirement 9: React App Scaffolding Inside Tauri

**User Story:** As a developer, I want a React application scaffolded inside the existing Tauri project, so that the new frontend integrates with the Tauri desktop shell.

#### Acceptance Criteria

1. THE React_App SHALL be scaffolded inside `PoC/astra-poc-vc/tauri-app/` with a standard React project structure (e.g., using Vite as the build tool).
2. THE React_App dev server SHALL run on port 7100 to match the existing Tauri `devUrl` configuration in `tauri.conf.json`.
3. THE React_App SHALL include CopilotKit as a dependency and configure the `<CopilotKit>` provider to connect to the backend SSE_Endpoint.
4. THE React_App SHALL include a layout with a chat panel and a dashboard area where agent-generated surfaces are rendered.
5. THE `start-dev.sh` script SHALL be updated to start both the Docker container (backend) and the React dev server before launching Tauri.

### Requirement 10: Component Type Coverage

**User Story:** As a developer, I want the initial Component_Map to cover all existing widget patterns using React components, so that the migration from vanilla JS to React is feature-complete.

#### Acceptance Criteria

1. THE Component_Map SHALL include a `StockTicker` React component that renders a stock ticker row displaying ticker symbol, company name, price, and change percentage, and emits a `stock_clicked` action when clicked.
2. THE Component_Map SHALL include a `StockAlert` React component that renders a notification banner with sentiment indicator (bullish/bearish/neutral), matched tickers, email source, and action buttons (dismiss, view details, refresh).
3. THE Component_Map SHALL include an `EmailRow` React component that renders an email row with sender avatar, subject, preview, timestamp, and hover actions (reply, summarize).
4. THE Component_Map SHALL include a `MetricCard` React component that renders a single metric with label, value, change indicator, and emits a `metric_clicked` action when clicked.
5. THE Component_Map SHALL include a `SparklineChart` React component that renders a mini chart from an array of numeric values with configurable accent color.
6. THE Component_Map SHALL include a `CalendarEvent` React component that renders a calendar event row with time, title, and location.
7. ALL existing widget patterns (dashboard, stock alert, email summary, calendar, travel info, metric cards) SHALL be reproducible using combinations of standard and custom React components in the Component_Map.

### Requirement 11: A2UI Message Serialization Round-Trip

**User Story:** As a developer, I want to ensure that A2UI JSON messages can be serialized and deserialized without data loss, so that the contract between agent and frontend is reliable.

#### Acceptance Criteria

1. FOR ALL valid A2UI messages (surfaceUpdate, beginRendering, deleteSurface), serializing to JSON and then deserializing SHALL produce an equivalent object (round-trip property).
2. THE serializer SHALL preserve the adjacency list structure including component IDs, child references, props values, and action definitions through the round-trip.
3. THE serializer SHALL handle Unicode text in component props, numeric values, boolean flags, and null/optional fields correctly through the round-trip.

### Requirement 12: Backward Compatibility During Migration

**User Story:** As a developer, I want the migration to be incremental, so that existing functionality continues to work while the new architecture is built.

#### Acceptance Criteria

1. WHILE the `render_widget` tool remains in the codebase, THE backend SHALL continue to handle raw HTML widget messages from the `render_widget` tool via the existing WebSocket endpoint.
2. THE existing WebSocket endpoint (`/ws`) SHALL remain functional alongside the new SSE_Endpoint during the migration period.
3. WHEN the vanilla JS frontend (`static/app.js`) is eventually removed, THE backend SHALL remove the WebSocket endpoint and the `render_widget` tool.
4. IF the AG-UI SSE_Endpoint encounters an unrecoverable error, THEN THE backend SHALL log the error and return an appropriate HTTP error response.

### Requirement 13: Progressive Streaming UX

**User Story:** As a user, I want to see the interface appear progressively as the agent generates it, so that I get immediate visual feedback.

#### Acceptance Criteria

1. WHEN the Astra_Agent streams text tokens, THE React_App SHALL display them progressively in the chat panel as they arrive.
2. WHEN the Astra_Agent emits a `surfaceUpdate` followed by `beginRendering`, THE React_App SHALL render the surface as soon as the `beginRendering` message is received, without waiting for the full agent turn to complete.
3. WHEN multiple surfaces are emitted in a single agent turn, THE React_App SHALL render each surface independently as its `beginRendering` message arrives.
4. THE React_App SHALL display a typing indicator or loading state while the agent is processing and streaming responses.

## Phased Implementation Strategy

### Phase 1 (MVP): React + CopilotKit + AG-UI End-to-End Pipeline

Scope: Get the new architecture working end-to-end. Agent emits A2UI JSON, AG-UI streams it via SSE, CopilotKit renders React components.

- Install `ag-ui-langgraph` and create SSE endpoint wrapping the existing LangGraph agent
- Scaffold React app inside `tauri-app/` with Vite, CopilotKit, and AIOS design system CSS
- Implement CopilotKit provider + `useAgent` hook connecting to SSE endpoint
- Implement Component_Map with AIOS-themed React components for standard catalog (Text, Button, Card, Row, Column, Divider, Tabs, Image, Icon, List)
- Implement custom Astra React components (StockTicker, StockAlert, EmailRow, MetricCard, SparklineChart, CalendarEvent)
- Create `emit_ui` tool in agent (passthrough — AG-UI carries the payload)
- Create `prompts/a2ui_catalog.md` component catalog prompt
- Update `prompts/system.md` to reference `emit_ui` instead of `render_widget` and HTML generation
- Update agent prompt composition to use `a2ui_catalog.md` instead of `design_system.md` + `widget_templates.md`
- Keep `render_widget` tool and WebSocket endpoint for backward compatibility
- All component values use literal props (no reactive data binding)
- `deleteSurface` support in React app

Requirements covered: 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13

### Phase 2: Reactive Data Binding

Scope: Add data model layer so stock prices, emails, etc. can update without regenerating the component tree.

- Implement `dataModelUpdate` message handling in CopilotKit/React layer
- Components can use `path` bindings (e.g., `{"path": "/stocks/AAPL/price"}`)
- Agent emits `dataModelUpdate` after tool calls like `get_stock_quote` to push fresh data
- React components reactively update when bound data changes

### Phase 3: Progressive Rendering and Incremental Updates

Scope: Optimize for streaming and partial updates.

- Incremental `surfaceUpdate` merging — agent can add/update individual components by ID
- Progressive rendering — agent streams components across multiple `surfaceUpdate` messages before `beginRendering`
- Input components (TextField, CheckBox, DateTimeInput, Slider) for interactive forms
- Remove legacy WebSocket endpoint and `render_widget` tool
- Remove vanilla JS frontend (`static/app.js`, `static/index.html`)
