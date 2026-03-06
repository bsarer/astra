# Implementation Plan: Tauri + Docker + WSS Architecture

## Overview

Migrate the Astra PoC from FastAPI+SSE to a Tauri desktop app with a Dockerized backend communicating over WebSockets. Implementation proceeds bottom-up: data models → backend WebSocket server → agent modifications → frontend rewrite → Docker container → Tauri shell. Each step builds on the previous, with tests validating correctness incrementally.

## Tasks

- [x] 1. Define typed message protocol data models
  - [x] 1.1 Create `PoC/astra-poc-vc/models.py` with all Message Protocol types
    - Define `TokenMessage`, `WidgetMessage`, `GridOptions`, `DoneMessage`, `ErrorMessage`, `SessionInitMessage` (server→client)
    - Define `UserMessage`, `WidgetEventMessage` (client→server)
    - Define `ServerMessage` and `ClientMessage` union types
    - Define `HealthResponse` model
    - Use `TypedDict` with `Literal` type fields as specified in the design
    - Add a `parse_client_message(raw: str) -> ClientMessage` helper that parses JSON and validates the `type` field
    - Add a `serialize_server_message(msg: ServerMessage) -> str` helper that serializes to JSON
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7_

  - [ ]* 1.2 Write property test for message protocol round-trip (Property 1)
    - **Property 1: Message protocol round-trip**
    - Use `hypothesis` to generate arbitrary valid `ServerMessage` and `ClientMessage` objects
    - Verify serializing to JSON and deserializing back preserves all required fields including `type` and type-specific fields
    - **Validates: Requirements 2.3, 2.4, 2.5, 2.6, 2.7**

- [x] 2. Implement session manager
  - [x] 2.1 Create `PoC/astra-poc-vc/session.py` with `SessionManager` class
    - Implement `get_or_create(session_id: str | None) -> str` that returns existing or generates new UUID
    - Implement `get_config(session_id: str) -> dict` that returns `{"configurable": {"thread_id": session_id}}`
    - Use the existing `MemorySaver` from `agent.py` — session_id maps directly to LangGraph thread_id
    - _Requirements: 8.1, 8.2, 8.3, 8.4_

  - [ ]* 2.2 Write property test for unique session ID generation (Property 11)
    - **Property 11: New unique session_id generated when none provided**
    - Use `hypothesis` to generate N calls to `get_or_create(None)` and verify all returned session_ids are unique UUIDs
    - **Validates: Requirements 8.4**

- [x] 3. Modify agent for secure code execution with timeout
  - [x] 3.1 Add 30-second timeout to `run_python_code` in `PoC/astra-poc-vc/agent.py`
    - Wrap code execution in `asyncio.wait_for` or use `signal.alarm` with a 30-second limit
    - On timeout, terminate execution and return a timeout error message string
    - Ensure exceptions from executed code are caught and returned as error strings without crashing the agent
    - Refactor `get_agent_response_stream` to accept `conversation_id` as a parameter (already does, but ensure it uses `SessionManager.get_config`)
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5_

  - [ ]* 3.2 Write property test for stdout capture round-trip (Property 12)
    - **Property 12: Code execution stdout capture round-trip**
    - Use `hypothesis` to generate arbitrary printable strings, wrap in `print()` calls, execute via `run_python_code`, verify output contains the printed value
    - **Validates: Requirements 9.2**

  - [ ]* 3.3 Write property test for exception-raising code (Property 13)
    - **Property 13: Exception-raising code returns error without crashing**
    - Use `hypothesis` to generate arbitrary exception messages, create code that raises them, verify `run_python_code` returns the exception message and remains callable afterward
    - **Validates: Requirements 9.3**

- [x] 4. Checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Implement WebSocket server endpoint and health check
  - [x] 5.1 Add health check endpoint to `PoC/astra-poc-vc/main.py`
    - Add `GET /health` route returning `{"status": "ok"}` with HTTP 200 when ready
    - Return HTTP 503 while the app is still initializing (use an app-level readiness flag)
    - _Requirements: 7.1, 7.2, 7.3_

  - [x] 5.2 Add WebSocket endpoint to `PoC/astra-poc-vc/main.py`
    - Add `@app.websocket("/ws")` handler accepting optional `session_id` query parameter
    - On connect: use `SessionManager.get_or_create(session_id)` and send `session_init` message
    - On `user_message`: invoke `get_agent_response_stream()` with the session's conversation_id
    - Stream agent events as typed JSON messages: `token` for `on_chat_model_stream`, `widget` for `render_widget` tool starts, `done` on stream completion
    - On `widget_event`: forward to agent as a `HumanMessage` with event context
    - On malformed JSON: send `error` message, keep connection open
    - On unhandled exception during agent processing: send `error` then `done`, keep connection open
    - Preserve the existing `POST /chat` endpoint temporarily for backward compatibility
    - Keep static file serving at `/` for browser fallback mode
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 5.1, 5.2, 8.1, 8.2, 8.3, 8.4_

  - [ ]* 5.3 Write property test for token event mapping (Property 2)
    - **Property 2: Agent token event maps to correct token message**
    - Use `hypothesis` to generate arbitrary text strings, simulate `on_chat_model_stream` events, verify the WebSocket produces `{"type": "token", "content": <text>}`
    - **Validates: Requirements 1.4, 2.3**

  - [ ]* 5.4 Write property test for widget event mapping (Property 3)
    - **Property 3: Agent widget event maps to correct widget message**
    - Use `hypothesis` to generate arbitrary `id`, `html`, `width_percent`, `height_px` values
    - Verify the produced message has correct `type`, `id`, `html`, and computed `grid` (w = clamp(width_percent * 12 / 100, 1, 12), h = max(1, height_px / 10))
    - **Validates: Requirements 1.5, 2.4**

  - [ ]* 5.5 Write property test for stream termination (Property 4)
    - **Property 4: Stream always terminates with done message**
    - Verify that for any completed agent invocation, the last message has `type` equal to `"done"`
    - **Validates: Requirements 1.6**

  - [ ]* 5.6 Write property test for malformed JSON handling (Property 5)
    - **Property 5: Malformed JSON produces error without closing connection**
    - Use `hypothesis` to generate arbitrary non-JSON strings, send over WebSocket, verify `error` response with non-empty `content` and connection remains open
    - **Validates: Requirements 1.7**

  - [ ]* 5.7 Write property test for valid client message routing (Property 14)
    - **Property 14: Valid client messages are parsed and routed to agent**
    - Use `hypothesis` to generate valid `user_message` JSON with non-empty `content`, verify the LangGraph agent is invoked with that content as a `HumanMessage`
    - **Validates: Requirements 1.2**

- [x] 6. Checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 7. Rewrite frontend WebSocket client
  - [x] 7.1 Implement `AgentConnection` class in `PoC/astra-poc-vc/static/app.js`
    - Create `AgentConnection` class with constructor that connects to `ws://` or `wss://` based on `window.location.protocol`
    - Derive WebSocket URL from page origin: `https:` → `wss://`, `http:` → `ws://`, preserving host and port
    - Implement `send(message)` method for sending typed JSON messages
    - Implement callback registration: `onToken`, `onWidget`, `onDone`, `onError`, `onSessionInit`
    - Implement `reconnect()` with exponential backoff: delays of 1s, 2s, 4s, 8s, 16s, max 5 retries
    - Implement `close()` for clean disconnection
    - Store `session_id` from `session_init` message and include it in reconnection URL
    - _Requirements: 3.1, 3.7, 5.3_

  - [x] 7.2 Rewrite `sendMessage` and event handling in `PoC/astra-poc-vc/static/app.js`
    - Remove the `fetch('/chat', ...)` POST logic and SSE reader from `sendMessage()`
    - Replace with sending `{"type": "user_message", "content": "..."}` via `AgentConnection.send()`
    - Wire `onToken` callback to append token content to current assistant message div
    - Wire `onWidget` callback to call existing `renderGenUIComponent()` function
    - Wire `onDone` callback to finalize response and call `setTyping(false)`
    - Wire `onError` callback to display error as system message via `appendMessage('system', ...)`
    - Rewrite `dispatchAgentEvent` to send `{"type": "widget_event", "event_name": "...", "payload": {...}}` over WebSocket
    - Initialize `AgentConnection` on `DOMContentLoaded`
    - _Requirements: 3.2, 3.3, 3.4, 3.5, 3.6, 3.8_

  - [ ]* 7.3 Write property test for message dispatch routing (Property 6)
    - **Property 6: Frontend dispatches messages to correct handlers by type**
    - Use `fast-check` to generate server messages of each type, verify routing: `token` → chat append, `widget` → `renderGenUIComponent`, `error` → system message, `done` → input re-enable
    - **Validates: Requirements 3.3, 3.4, 3.5, 3.6**

  - [ ]* 7.4 Write property test for reconnection backoff (Property 7)
    - **Property 7: Reconnection follows exponential backoff with max 5 retries**
    - Use `fast-check` to generate sequences of disconnections, verify delays follow 1s, 2s, 4s, 8s, 16s pattern with max 5 attempts
    - **Validates: Requirements 3.7**

  - [ ]* 7.5 Write property test for widget event bridge (Property 8)
    - **Property 8: Widget event bridge produces correct WebSocket message**
    - Use `fast-check` to generate arbitrary `event_name` strings and `payload` objects, verify the sent WebSocket message matches `{"type": "widget_event", "event_name": ..., "payload": ...}`
    - **Validates: Requirements 3.8**

  - [ ]* 7.6 Write property test for WebSocket URL derivation (Property 9)
    - **Property 9: WebSocket URL derived correctly from page origin**
    - Use `fast-check` to generate origins with `http:` and `https:` protocols, verify `ws://` and `wss://` derivation with preserved host and port
    - **Validates: Requirements 5.3**

- [x] 8. Checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 9. Create Docker container configuration
  - [x] 9.1 Create `PoC/astra-poc-vc/Dockerfile`
    - Use `python:3.12-slim` base image
    - Create non-root `agent` user with `useradd`
    - Copy `requirements.txt` and install dependencies with `pip install --no-cache-dir`
    - Copy application files
    - Switch to `agent` user
    - Expose port 8000
    - Set CMD to `uvicorn main:app --host 0.0.0.0 --port 8000`
    - _Requirements: 4.1, 4.2, 4.5_

  - [x] 9.2 Create `PoC/astra-poc-vc/docker-compose.yml` with security flags
    - Configure service with `--no-new-privileges` and `--cap-drop=ALL`
    - Pass `OPENAI_API_KEY` and `OPENAI_MODEL` as environment variables
    - Map port 8000
    - _Requirements: 4.3, 4.4, 4.6, 9.6_

  - [x] 9.3 Create `PoC/astra-poc-vc/.dockerignore`
    - Exclude `.venv/`, `__pycache__/`, `.env`, `.git/`, `node_modules/`
    - _Requirements: 4.1_

- [x] 10. Implement Tauri desktop shell
  - [x] 10.1 Initialize Tauri project structure
    - Create `PoC/astra-poc-vc/tauri-app/src-tauri/` directory structure
    - Create `Cargo.toml` with Tauri dependencies
    - Create `tauri.conf.json` with external URL configuration (no bundled frontend), window title "Astra", default size 1400×900
    - _Requirements: 6.1, 6.4, 6.7_

  - [x] 10.2 Implement Docker lifecycle management in `main.rs`
    - On app start: check if container is running via `docker ps`, start with `docker run` if not
    - Pass `--no-new-privileges --cap-drop=ALL` security flags and env vars to `docker run`
    - Poll `GET /health` endpoint until HTTP 200 response (timeout after 60s)
    - On successful health check: load webview URL `http://localhost:{port}/`
    - On timeout (60s): show error dialog with failure reason
    - On window close: run `docker stop {container_name}` for graceful shutdown
    - Make port configurable via settings/config file
    - _Requirements: 6.2, 6.3, 6.5, 6.6, 6.7_

  - [ ]* 10.3 Write property test for session resume (Property 10)
    - **Property 10: Session resume via session_id**
    - Create a session, send messages, disconnect, reconnect with same `session_id`, verify the agent has access to prior message history
    - **Validates: Requirements 8.3**

- [x] 11. Final checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document
- The existing `POST /chat` endpoint is preserved temporarily in task 5.2 for backward compatibility during migration
- Backend uses Python with `hypothesis` for property tests; frontend uses JavaScript with `fast-check`
