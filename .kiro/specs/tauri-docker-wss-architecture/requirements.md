# Requirements Document

## Introduction

This document specifies the requirements for migrating the existing Astra PoC (a LangGraph-based AI agent with a generative UI canvas) from a plain FastAPI+SSE web application into a Tauri desktop application with the agent backend running inside a Docker container, communicating over WebSockets (WSS). The migration preserves the existing HTML/JS frontend, wraps it in Tauri's webview, isolates the backend in Docker for security (especially for `run_python_code`), and replaces the SSE+POST communication pattern with a single bidirectional WebSocket connection. A browser fallback mode is retained so the same Docker container can serve the app to plain browsers.

## Glossary

- **Tauri_Shell**: The native desktop application built with Tauri that hosts the frontend webview and manages the Docker backend lifecycle.
- **Agent_Backend**: The FastAPI + LangGraph server running inside a Docker container, responsible for processing user messages, executing tools, and streaming responses.
- **WebSocket_Server**: The FastAPI WebSocket endpoint inside the Agent_Backend that handles bidirectional communication with clients.
- **Message_Protocol**: The typed JSON message format used for all communication between clients and the Agent_Backend over WebSocket.
- **Docker_Container**: The isolated Linux container running the Agent_Backend, built from a Dockerfile in the project.
- **Frontend**: The existing HTML/JS/CSS application (index.html, app.js) with GridStack canvas and iframe-based widget rendering.
- **Browser_Client**: A plain web browser connecting to the Agent_Backend directly (fallback mode without Tauri).
- **Widget_Event**: A JSON message sent from an iframe widget back to the agent via the `dispatchAgentEvent` bridge.
- **Code_Sandbox**: The isolated execution environment inside the Docker_Container where `run_python_code` executes user-provided Python code.

## Requirements

### Requirement 1: WebSocket Server Endpoint

**User Story:** As a developer, I want the Agent_Backend to expose a WebSocket endpoint, so that clients can send and receive messages over a single persistent connection instead of using separate SSE streams and POST requests.

#### Acceptance Criteria

1. THE WebSocket_Server SHALL accept WebSocket connections on the `/ws` path.
2. WHEN a client sends a valid JSON message over the WebSocket connection, THE WebSocket_Server SHALL parse the message and route it to the LangGraph agent for processing.
3. WHILE a LangGraph agent invocation is in progress, THE WebSocket_Server SHALL stream response events back to the client as individual JSON messages over the same WebSocket connection.
4. WHEN the LangGraph agent emits a text token via `on_chat_model_stream`, THE WebSocket_Server SHALL send a Message_Protocol message of type `token` containing the text content.
5. WHEN the LangGraph agent invokes the `render_widget` tool, THE WebSocket_Server SHALL send a Message_Protocol message of type `widget` containing the widget id, html, and grid dimensions.
6. WHEN the agent finishes processing a user message, THE WebSocket_Server SHALL send a Message_Protocol message of type `done` to signal stream completion.
7. IF a client sends a malformed JSON message, THEN THE WebSocket_Server SHALL send a Message_Protocol message of type `error` with a descriptive error string and keep the connection open.
8. IF an unhandled exception occurs during agent processing, THEN THE WebSocket_Server SHALL send a Message_Protocol message of type `error` with the exception description and keep the connection open.

### Requirement 2: Typed JSON Message Protocol

**User Story:** As a developer, I want a well-defined typed JSON message protocol, so that both the frontend and backend have a clear contract for all WebSocket communication.

#### Acceptance Criteria

1. THE Message_Protocol SHALL define the following server-to-client message types: `token`, `widget`, `done`, and `error`.
2. THE Message_Protocol SHALL define the following client-to-server message types: `user_message` and `widget_event`.
3. WHEN a `token` message is sent, THE Message_Protocol SHALL include a `content` field containing the text string.
4. WHEN a `widget` message is sent, THE Message_Protocol SHALL include `id`, `html`, and `grid` fields matching the existing widget data structure.
5. WHEN a `user_message` is received, THE Message_Protocol SHALL include a `content` field containing the user's text.
6. WHEN a `widget_event` is received, THE Message_Protocol SHALL include `event_name` and `payload` fields.
7. THE Message_Protocol SHALL include a `type` field in every message to identify the message kind.

### Requirement 3: Frontend WebSocket Client

**User Story:** As a developer, I want the frontend to communicate with the Agent_Backend over WebSocket instead of SSE+POST, so that the app uses a single bidirectional connection for all messaging.

#### Acceptance Criteria

1. WHEN the Frontend loads, THE Frontend SHALL establish a WebSocket connection to the Agent_Backend at the `/ws` endpoint.
2. WHEN the user submits a chat message, THE Frontend SHALL send a `user_message` Message_Protocol message over the WebSocket connection instead of making a POST request.
3. WHEN the Frontend receives a `token` message, THE Frontend SHALL append the token content to the current assistant message in the chat panel.
4. WHEN the Frontend receives a `widget` message, THE Frontend SHALL render the widget on the GridStack canvas using the existing `renderGenUIComponent` function.
5. WHEN the Frontend receives a `done` message, THE Frontend SHALL finalize the current assistant response and re-enable the input controls.
6. WHEN the Frontend receives an `error` message, THE Frontend SHALL display the error content as a system message in the chat panel.
7. IF the WebSocket connection is lost, THEN THE Frontend SHALL attempt to reconnect with exponential backoff up to 5 retries.
8. WHEN a widget dispatches an event via `dispatchAgentEvent`, THE Frontend SHALL send a `widget_event` Message_Protocol message over the WebSocket connection instead of calling `sendMessage`.

### Requirement 4: Docker Container for Agent Backend

**User Story:** As a developer, I want the Agent_Backend to run inside a Docker container, so that the `run_python_code` tool executes in an isolated environment and the backend is portable across machines.

#### Acceptance Criteria

1. THE Docker_Container SHALL be built from a Dockerfile that installs all Python dependencies from `requirements.txt`.
2. THE Docker_Container SHALL expose a single port (default 8000) for the WebSocket_Server and static file serving.
3. WHEN the Docker_Container starts, THE Agent_Backend SHALL be ready to accept WebSocket connections within 30 seconds.
4. THE Docker_Container SHALL accept the `OPENAI_API_KEY` and `OPENAI_MODEL` configuration values as environment variables.
5. THE Docker_Container SHALL run the Agent_Backend process as a non-root user.
6. WHEN `run_python_code` executes inside the Docker_Container, THE Code_Sandbox SHALL have no access to the host filesystem outside the container.

### Requirement 5: Browser Fallback Mode

**User Story:** As a developer, I want the same Docker container to serve the frontend to plain browsers, so that the app can be used without Tauri installed.

#### Acceptance Criteria

1. THE Agent_Backend SHALL serve the Frontend static files (index.html, app.js, CSS) at the root path `/`.
2. WHEN a Browser_Client navigates to the Agent_Backend URL, THE Agent_Backend SHALL serve the Frontend HTML page.
3. THE Frontend SHALL determine the WebSocket URL dynamically based on the current page origin (using `ws://` or `wss://` derived from `http://` or `https://`).
4. WHEN accessed via a Browser_Client, THE Frontend SHALL function identically to when accessed via the Tauri_Shell webview.

### Requirement 6: Tauri Desktop Shell

**User Story:** As a developer, I want a Tauri desktop application that wraps the existing frontend in a native window and manages the Docker backend lifecycle, so that the app feels like a native desktop application.

#### Acceptance Criteria

1. THE Tauri_Shell SHALL display the Frontend in a native webview window.
2. WHEN the Tauri_Shell starts, THE Tauri_Shell SHALL check whether the Docker_Container is already running and start it if it is not.
3. WHEN the Tauri_Shell starts the Docker_Container, THE Tauri_Shell SHALL wait until the Agent_Backend health endpoint responds before loading the Frontend.
4. THE Tauri_Shell SHALL load the Frontend from the Agent_Backend URL served by the Docker_Container (not from bundled local files).
5. WHEN the user closes the Tauri_Shell window, THE Tauri_Shell SHALL stop the Docker_Container gracefully.
6. IF the Docker_Container fails to start within 60 seconds, THEN THE Tauri_Shell SHALL display an error dialog to the user with the failure reason.
7. THE Tauri_Shell SHALL allow the user to configure the Docker_Container port via a settings mechanism.

### Requirement 7: Health Check Endpoint

**User Story:** As a developer, I want the Agent_Backend to expose a health check endpoint, so that the Tauri_Shell and monitoring tools can verify the backend is ready.

#### Acceptance Criteria

1. THE Agent_Backend SHALL expose a GET `/health` endpoint.
2. WHEN the Agent_Backend is ready to accept WebSocket connections, THE `/health` endpoint SHALL return an HTTP 200 response with a JSON body containing `{"status": "ok"}`.
3. WHILE the Agent_Backend is still initializing, THE `/health` endpoint SHALL return an HTTP 503 response.

### Requirement 8: Conversation Session Management

**User Story:** As a developer, I want WebSocket connections to maintain conversation state, so that the LangGraph agent preserves context across multiple messages within a session.

#### Acceptance Criteria

1. WHEN a WebSocket connection is established, THE WebSocket_Server SHALL create or resume a conversation session tied to that connection.
2. WHILE a WebSocket connection remains open, THE WebSocket_Server SHALL maintain the LangGraph memory checkpoint for that session.
3. WHEN a WebSocket connection is closed and re-established, THE WebSocket_Server SHALL allow the client to resume a previous session by providing a `session_id` in the initial connection URL query parameter.
4. IF no `session_id` is provided, THEN THE WebSocket_Server SHALL create a new session with a unique identifier and send it to the client in a Message_Protocol message of type `session_init`.

### Requirement 9: Secure Code Execution in Docker

**User Story:** As a developer, I want the `run_python_code` tool to execute safely inside the Docker container, so that arbitrary user-provided code cannot compromise the host system.

#### Acceptance Criteria

1. WHEN `run_python_code` is invoked, THE Code_Sandbox SHALL execute the provided Python code inside the Docker_Container process.
2. THE Code_Sandbox SHALL capture stdout output from the executed code and return it as the tool result.
3. IF the executed code raises an exception, THEN THE Code_Sandbox SHALL return the exception message as the tool result without crashing the Agent_Backend.
4. THE Code_Sandbox SHALL enforce a maximum execution timeout of 30 seconds per invocation.
5. IF the executed code exceeds the 30-second timeout, THEN THE Code_Sandbox SHALL terminate the execution and return a timeout error message.
6. THE Docker_Container SHALL run with `--no-new-privileges` and drop all unnecessary Linux capabilities to limit the blast radius of executed code.
