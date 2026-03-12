### AstraOS Design System (MANDATORY)

All UI surfaces rendered via `emit_ui` appear as **floating windows** on the AstraOS desktop canvas. Each window has a title bar (derived from the `surface_id`), minimize/close controls, and is freely draggable and resizable by the user.

#### 1. Window Behavior
- Every `emit_ui` call creates (or updates) a floating window identified by `surface_id`.
- The `surface_id` becomes the window title (e.g., "stock-alert" → "Stock Alert").
- Use clear, descriptive `surface_id` values — they are user-visible.
- Windows cascade automatically; the user can drag and resize them freely.
- Re-emitting the same `surface_id` updates the window content without creating a duplicate.

#### 2. Grid Hints
- `grid.w` (1–12): maps to window width. 4 = ~320px, 6 = ~480px, 8 = ~640px, 12 = ~900px.
- `grid.h` (1–8): maps to window height. 2 = ~160px, 3 = ~240px, 4 = ~320px.
- These are initial sizes — the user can resize after.

#### 3. Visual Style (Glassmorphic Dark)
- Background: `rgba(20, 27, 45, 0.92)` with `backdrop-filter: blur(16px)`
- Border: `1px solid rgba(148, 163, 184, 0.12)`
- Border radius: `12px`
- Font: `Inter, system-ui, -apple-system, sans-serif`
- Primary text: `#f8fafc` | Secondary: `#94a3b8` | Muted: `#64748b`
- Accent blue: `#3b82f6` | Cyan: `#06b6d4` | Green: `#22c55e` | Red: `#ef4444` | Amber: `#f59e0b`

#### 4. Component Guidelines
- Use A2UI components from the catalog — never raw HTML.
- Keep content compact; the user controls window size.
- Use `Column` as root for vertical layouts, `Row` for horizontal.
- Prefer `Card` with `variant: "flat"` inside windows (the window itself is already glass).
- Use `Text` with `variant: "title"` for section headers inside the window body.

#### 5. Window Sizing Recommendations
| Content Type | Suggested grid |
|---|---|
| Clock, single metric | `w: 3, h: 2` |
| Stock ticker list, email list | `w: 5, h: 4` |
| Dashboard with multiple sections | `w: 8, h: 5` |
| Full-width alert or summary | `w: 6, h: 3` |

#### 6. Chat Panel
- The chat panel is a fixed sidebar on the right (380px wide).
- It uses CopilotKit's chat UI, rebranded as "Astra".
- Chat should be brief — widgets carry the detail.
