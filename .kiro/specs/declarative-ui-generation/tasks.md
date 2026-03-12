# Implementation Plan: Declarative UI Generation (React + CopilotKit + AG-UI — Phase 1 MVP)

## Overview

Phase 1 implements the new architecture end-to-end: the agent emits A2UI JSON via `emit_ui` tool, `ag-ui-langgraph` streams it over SSE, and a React + CopilotKit frontend renders AIOS-themed components. The `render_widget` tool and WebSocket `/ws` endpoint are kept for backward compatibility. All component values use literal props (no reactive data binding). The old `a2ui_renderer.py` is deleted — no server-side HTML rendering.

## Tasks

- [x] 1. A2UI message models (already complete)
  - [x] 1.1 `PoC/astra-poc-vc/a2ui_models.py` — Pydantic models for A2UIComponent, SurfaceUpdate, BeginRendering, DeleteSurface, DataModelUpdate stub, A2UIMessage union
    - _Requirements: 1.1, 1.2, 1.3, 2.1, 2.2_

  - [ ]* 1.2 Write property test for A2UI message round-trip serialization
    - **Property 1: A2UI Message Serialization Round-Trip**
    - **Validates: Requirements 11.1, 11.2, 11.3**

  - [ ]* 1.3 Write property test for adjacency list structural invariant
    - **Property 2: Adjacency List Structural Invariant**
    - **Validates: Requirements 2.1, 2.2**

- [x] 2. Backend: Add `emit_ui` tool and AG-UI SSE endpoint
  - [x] 2.1 Add `emit_ui` tool in `PoC/astra-poc-vc/agent.py`
    - Define `emit_ui(surface_id: str, components: list[dict], grid: dict | None = None) -> str` as a passthrough tool
    - Returns `f"Surface {surface_id} emitted with {len(components)} components."`
    - Add to the `tools` list alongside existing tools; keep `render_widget` for backward compat
    - _Requirements: 6.1, 8.3, 8.4_

  - [x] 2.2 Add `ag-ui-langgraph` dependency and SSE endpoint in `PoC/astra-poc-vc/main.py`
    - Add `ag-ui-langgraph` to `requirements.txt`
    - Import `create_adapter` from `ag_ui_langgraph`, create adapter wrapping the compiled `graph`
    - Add `POST /api/copilotkit` FastAPI route that delegates to `agui_adapter.handle(request)`
    - Keep existing `/ws`, `/health`, `/chat` routes unchanged
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 8.1, 8.2, 8.5, 12.2, 12.4_

  - [x] 2.3 Delete `PoC/astra-poc-vc/a2ui_renderer.py`
    - Remove the old server-side HTML renderer — no longer needed
    - _Requirements: 7.2_

  - [ ]* 2.4 Write property test for `emit_ui` passthrough behavior
    - **Property 5: emit_ui Tool Is a Passthrough**
    - **Validates: Requirements 6.1, 8.3**

- [x] 3. Agent prompts: Create catalog, update system prompt, update composition
  - [x] 3.1 Create `PoC/astra-poc-vc/prompts/a2ui_catalog.md`
    - A2UI adjacency list format specification with one complete example
    - Standard catalog: Text, Button, Card, Row, Column, Divider, Tabs, Image, Icon, List — type name + props schema
    - Custom Astra catalog: StockTicker, StockAlert, EmailRow, MetricCard, SparklineChart, CalendarEvent — type name + props schema
    - Instructions: emit `surfaceUpdate` then `beginRendering`, use descriptive IDs, reference children by ID
    - Target ~800 tokens
    - _Requirements: 6.3, 7.1_

  - [x] 3.2 Update `PoC/astra-poc-vc/prompts/system.md`
    - Remove all HTML generation instructions, CSS design system rules, iframe/JS references
    - Add instructions to use `emit_ui` tool for UI generation
    - Reference the A2UI component catalog for available components
    - Keep `run_python_code`, `install_python_packages`, backend instructions
    - _Requirements: 6.2, 7.3_

  - [x] 3.3 Update `SYSTEM_PROMPT` composition in `PoC/astra-poc-vc/agent.py`
    - Change from `load_prompt("system") + load_prompt("design_system") + load_prompt("widget_templates") + load_prompt("persona_context")`
    - To `load_prompt("system") + load_prompt("a2ui_catalog") + load_prompt("persona_context")`
    - _Requirements: 7.1, 7.2_

  - [x] 3.4 Update `PoC/astra-poc-vc/prompts/persona_context.md` dashboard guidelines
    - Replace `render_widget` references with `emit_ui` in the dashboard and stock alert guidelines
    - _Requirements: 6.4, 6.5_

  - [ ]* 3.5 Write property test for agent prompt containing no HTML/CSS/JS
    - **Property 3: Agent Prompt Contains No HTML/CSS/JS**
    - **Validates: Requirements 6.2, 7.3**

- [ ] 4. Checkpoint — Backend and prompt changes
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Frontend: Scaffold React app with Vite and CopilotKit
  - [x] 5.1 Initialize React + Vite project in `PoC/astra-poc-vc/tauri-app/`
    - Create `package.json` with dependencies: `react`, `react-dom`, `@copilotkit/react-core`, `@copilotkit/react-ui`
    - Create `vite.config.ts` — dev server on port 7100, proxy `/api` to `http://localhost:7101`
    - Create `tsconfig.json` for TypeScript
    - Create `index.html` (Vite entry)
    - Create `src/main.tsx` (React entry point)
    - _Requirements: 9.1, 9.2, 9.3_

  - [x] 5.2 Create AIOS design system theme in `PoC/astra-poc-vc/tauri-app/src/theme/aios.css`
    - CSS custom properties: `--bg-panel`, `--bg-card`, `--bg-card-hover`, `--accent-blue`, `--accent-cyan`, `--accent-green`, `--accent-red`, `--accent-amber`, `--text-primary`, `--text-secondary`, `--text-muted`, `--border-subtle`, `--glass-blur`, `--radius-md`, `--radius-lg`, `--font-family`, `--transition-fast`
    - Base styles for `.aios-card--glass`, `.aios-card--flat`, `.aios-card--outlined`, `.aios-btn`, `.aios-text` variants
    - Import Inter font
    - _Requirements: 5.3_

  - [x] 5.3 Create root `App.tsx` with CopilotKit provider
    - Wrap app with `<CopilotKit runtimeUrl="http://localhost:7100/api/copilotkit">`
    - Layout: `<Dashboard />` + `<ChatPanel />` side by side
    - Import `aios.css` theme
    - _Requirements: 4.1, 4.2, 9.3, 9.4_

- [x] 6. Frontend: Implement standard AIOS React components
  - [x] 6.1 Create standard components in `PoC/astra-poc-vc/tauri-app/src/components/aios/`
    - `AIOSText.tsx` — `text`, `variant` (title/body/secondary/muted), `weight`
    - `AIOSButton.tsx` — `label`, `action`, `payload`, `variant` (primary/secondary/ghost), `onAction` callback
    - `AIOSCard.tsx` — `children`, `padding`, `variant` (glass/flat/outlined)
    - `AIOSRow.tsx` — `children`, `gap`, `align`, `wrap`
    - `AIOSColumn.tsx` — `children`, `gap`, `align`
    - `AIOSDivider.tsx` — `spacing`
    - `AIOSTabs.tsx` — `labels`, `active`, `children` (one per tab), `onTabChange` callback, local state management
    - `AIOSImage.tsx` — `src`, `alt`, `width`, `height`
    - `AIOSIcon.tsx` — `name`, `size`, `color`
    - `AIOSList.tsx` — `ordered`, `children`
    - `AIOSFallback.tsx` — renders unknown type name + raw props as formatted JSON in a Card
    - _Requirements: 5.1, 5.3, 5.4, 5.5, 5.6_

  - [ ]* 6.2 Write property test for Button emitting action on click
    - **Property 8: Button Component Emits Action on Click**
    - **Validates: Requirements 5.5**

  - [ ]* 6.3 Write property test for Tabs managing state and emitting event
    - **Property 9: Tabs Component Manages State and Emits Event**
    - **Validates: Requirements 5.6**

  - [ ]* 6.4 Write property test for Fallback rendering unknown types
    - **Property 7: Fallback Component Renders for Unknown Types**
    - **Validates: Requirements 5.4**

- [x] 7. Frontend: Implement custom Astra React components
  - [x] 7.1 Create custom components in `PoC/astra-poc-vc/tauri-app/src/components/aios/`
    - `AIOSStockTicker.tsx` — `ticker`, `company`, `price`, `change_pct`, `stock_clicked` action on click
    - `AIOSStockAlert.tsx` — `title`, `source`, `sentiment` (bullish/bearish/neutral), `tickers` list, `actions` buttons
    - `AIOSEmailRow.tsx` — `email_id`, `from_name`, `initial`, `subject`, `preview`, `time`, hover actions
    - `AIOSMetricCard.tsx` — `label`, `value`, `change`, `color`, `metric_clicked` action
    - `AIOSSparklineChart.tsx` — `values` array, `color`, `height`
    - `AIOSCalendarEvent.tsx` — `time`, `title`, `location`, `attendees`
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.7_

- [x] 8. Frontend: Wire CopilotKit provider, A2UI renderer, and Component_Map
  - [x] 8.1 Create `PoC/astra-poc-vc/tauri-app/src/components/componentMap.ts`
    - Map all standard types (Text, Button, Card, Row, Column, Divider, Tabs, Image, Icon, List) to AIOS components
    - Map all custom types (StockTicker, StockAlert, EmailRow, MetricCard, SparklineChart, CalendarEvent) to AIOS components
    - Export `fallbackComponent` pointing to `AIOSFallback`
    - _Requirements: 4.4, 5.1, 5.2, 10.1–10.6_

  - [x] 8.2 Implement `PoC/astra-poc-vc/tauri-app/src/components/Dashboard.tsx`
    - Use CopilotKit's A2UI renderer with `componentMap` and `fallbackComponent`
    - Render agent-generated surfaces in the dashboard area
    - Handle `deleteSurface` by removing surfaces from state
    - _Requirements: 4.3, 4.5, 13.2, 13.3_

  - [x] 8.3 Implement `PoC/astra-poc-vc/tauri-app/src/components/ChatPanel.tsx`
    - Use CopilotKit's `useAgent` hook to get messages and `sendMessage`
    - Display streamed text tokens progressively
    - Show typing indicator while agent is processing
    - Provide text input for user messages
    - _Requirements: 4.6, 13.1, 13.4_

  - [ ]* 8.4 Write property test for Component_Map covering all catalog types
    - **Property 4: Component_Map Covers All A2UI Catalog Types**
    - **Validates: Requirements 4.4, 5.1, 5.2, 10.1–10.6**

  - [ ]* 8.5 Write property test for DeleteSurface removing surface from state
    - **Property 6: DeleteSurface Removes Surface from State**
    - **Validates: Requirements 4.5**

- [ ] 9. Checkpoint — Frontend components and wiring
  - Ensure all tests pass, ask the user if questions arise.

- [x] 10. Infrastructure: Update ports, start-dev.sh, docker-compose
  - [x] 10.1 Update `PoC/astra-poc-vc/docker-compose.yml` port mapping
    - Change `7100:8000` to `7101:8000` (backend now on 7101, React dev server on 7100)
    - _Requirements: 9.2_

  - [x] 10.2 Update `PoC/astra-poc-vc/tauri-app/start-dev.sh`
    - Change Docker port from `7100:8000` to `7101:8000`
    - Add React dev server startup (`npm run dev` in `tauri-app/`) before Tauri
    - Wait for React dev server on port 7100 before launching Tauri
    - Cleanup React dev server PID on exit
    - _Requirements: 9.5_

- [ ] 11. Final checkpoint — Full integration
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Task 1.1 is already complete — `a2ui_models.py` exists with all Pydantic models
- The old `a2ui_renderer.py` is deleted in task 2.3 — no server-side HTML rendering in the new architecture
- `render_widget` tool and WebSocket `/ws` are kept for backward compatibility (Requirement 12)
- `design_system.md` and `widget_templates.md` are removed from prompt composition but NOT deleted from disk
- Phase 2 (reactive data binding) and Phase 3 (incremental updates) are out of scope
- Python property tests use `hypothesis`; TypeScript property tests use `fast-check` + `@testing-library/react` + `vitest`
