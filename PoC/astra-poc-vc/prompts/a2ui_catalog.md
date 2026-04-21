### A2UI Component Catalog

You generate UI by calling the `emit_ui` tool with a `surface_id` and a flat list of `components` in **adjacency list format**. Layout components reference children by ID — never nest component objects.

#### Component Format
```json
{"id": "my-card", "type": "Card", "props": {"variant": "glass"}, "children": ["title", "body"]}
```

#### Standard Components

| Type | Props | Children |
|------|-------|----------|
| Text | text, variant (title/body/secondary/muted), weight (bold/semibold/normal) | — |
| Button | label, action, payload, variant (primary/secondary/ghost) | — |
| Card | padding, variant (glass/flat/outlined) | Yes |
| Row | gap, align (start/center/end/stretch), wrap | Yes |
| Column | gap, align | Yes |
| Divider | spacing | — |
| Tabs | labels (list), active (index) | Yes (one child per tab) |
| Image | src, alt, width, height | — |
| Icon | name, size, color | — |
| List | ordered | Yes |

#### Custom Astra Components

| Type | Props |
|------|-------|
| StockTicker | ticker, company, price, change_pct |
| StockWatchlist | title (optional — self-refreshing, fetches live data via SSE every 60s, shows "last refreshed") |
| StockAlert | title, source, sentiment (bullish/bearish/neutral), tickers (list of {ticker, price, change_pct}), actions (list of {label, action}) |
| EmailRow | email_id, from_name, initial, subject, preview, time, actions |
| MetricCard | label, value, change, color |
| SparklineChart | values (list of numbers), color (green/red/blue/cyan), height |
| CalendarEvent | time, title, location, attendees |
| Clock | timezone (e.g. "America/New_York", optional — defaults to local), format ("12h"/"24h"), showDate (bool), label |
| FileExplorer | title, subtitle, query, category, timeframe, directory, sort |
| FileViewer | path or filename, optional preview_type/raw_url/viewer metadata; renders the raw file, not a preview summary |

#### Example: Mike's Dashboard (use this when user says "show me my dashboard")
Call `emit_ui` immediately with this structure — no data fetching needed, render from persona context:

```json
emit_ui(
  surface_id="mike-dashboard",
  components=[
    {"id": "root", "type": "Column", "props": {"gap": "16px"}, "children": ["greeting", "stats-row", "actions"]},
    {"id": "greeting", "type": "Card", "props": {"variant": "glass"}, "children": ["greet-text", "greet-sub"]},
    {"id": "greet-text", "type": "Text", "props": {"text": "Good morning, Mike 👋", "variant": "title", "weight": "bold"}, "children": []},
    {"id": "greet-sub", "type": "Text", "props": {"text": "Vertex Solutions · Austin, TX", "variant": "muted"}, "children": []},
    {"id": "stats-row", "type": "Row", "props": {"gap": "12px", "wrap": true}, "children": ["m1", "m2", "m3"]},
    {"id": "m1", "type": "MetricCard", "props": {"label": "Q1 Target", "value": "$1.2M", "change": "87% attained", "color": "cyan"}, "children": []},
    {"id": "m2", "type": "MetricCard", "props": {"label": "Key Clients", "value": "3", "change": "Acme · BluePeak · NovaTech", "color": "blue"}, "children": []},
    {"id": "m3", "type": "MetricCard", "props": {"label": "Team", "value": "3 reps", "change": "Sarah · Jake · Priya", "color": "green"}, "children": []},
    {"id": "actions", "type": "Row", "props": {"gap": "8px", "wrap": true}, "children": ["b1", "b2", "b3", "b4"]},
    {"id": "b1", "type": "Button", "props": {"label": "📧 Inbox", "action": "show_inbox", "variant": "secondary"}, "children": []},
    {"id": "b2", "type": "Button", "props": {"label": "📅 Calendar", "action": "show_calendar", "variant": "secondary"}, "children": []},
    {"id": "b3", "type": "Button", "props": {"label": "📈 Stocks", "action": "show_stocks", "variant": "secondary"}, "children": []},
    {"id": "b4", "type": "Button", "props": {"label": "📁 Files", "action": "show_files", "variant": "secondary"}, "children": []}
  ],
  grid={"w": 7, "h": 6}
)
```


#### Example: Stock Watchlist (use when user says "show me my stocks" or action "show_stocks")
Use `StockWatchlist` — it auto-refreshes every 60s via SSE and shows "last refreshed". No need to call `get_watchlist_summary` first.

```json
emit_ui(
  surface_id="stock-watchlist",
  components=[
    {"id": "root", "type": "Column", "props": {"gap": "8px"}, "children": ["watchlist"]},
    {"id": "watchlist", "type": "StockWatchlist", "props": {"title": "📈 Stock Watchlist"}, "children": []}
  ],
  grid={"w": 5, "h": 6}
)
```

```json
emit_ui(
  surface_id="stock-alert",
```
  components=[
    {"id": "root", "type": "Column", "props": {"gap": "12px"}, "children": ["banner", "tickers"]},
    {"id": "banner", "type": "StockAlert", "props": {"title": "Market Alert", "source": "Bloomberg Newsletter", "sentiment": "bullish", "tickers": [{"ticker": "AAPL", "price": 189.50, "change_pct": 2.3}], "actions": [{"label": "View Details", "action": "view_details"}]}},
    {"id": "tickers", "type": "Row", "props": {"gap": "8px"}, "children": ["t1"]},
    {"id": "t1", "type": "StockTicker", "props": {"ticker": "AAPL", "company": "Apple Inc.", "price": 189.50, "change_pct": 2.3}}
  ]
)
```

#### Rules
- Use descriptive IDs (e.g., "inbox-summary", "trip-card", not "c1", "c2")
- The first component is the root
- Always call `emit_ui` — never output raw HTML

#### Example: File List Surface
When the user asks "show me my files", "show me files", or action "show_files":
1. Call `list_user_files()` for the root `Files` directory unless the user explicitly names a folder
2. It returns JSON with a `files` array, each with `filename`, `type`, `size_kb`, `domains`
3. Prefer a single `FileExplorer` component instead of manually building rows.

```json
emit_ui(
  surface_id="my-files",
  components=[
    {"id": "root", "type": "FileExplorer", "props": {"title": "My Files", "subtitle": "Browse your root Files directory and open any file you need."}, "children": []}
  ],
  grid={"w": 6, "h": 7}
)
```
Use the exact type name `FileExplorer`. Do not use `AIOSFileExplorer` or lowercase variants unless the frontend explicitly aliases them.
Use props to make the widget reflect the user's request. Examples:
- Open a folder: `{"directory": "Downloads"}`
- Search by intent: `{"query": "pricing"}`
- Show only documents: `{"category": "documents"}`
- Group by file type: `{"sort": "type-asc"}`
- Never say files were changed unless you first called a file mutation tool.

When the user asks to organize, categorize, or separate files by type, name, or meaning:
1. Call `categorize_user_files(...)`
2. Then render a refreshed `FileExplorer`, usually pointed at the root or the chosen destination folder
3. Mention the grouping mode in the widget title or subtitle when helpful

Examples:
- Categorize by type: call `categorize_user_files(group_by="type")`
- Separate by meaning: call `categorize_user_files(group_by="meaning")`
- Preview by name first: call `categorize_user_files(group_by="name", dry_run=true)`

#### Example: File Content Surface
When the user asks to open a specific file, read a named file, show a PDF, or preview an image:
1. Call `open_user_file(filename)` to resolve the file path and raw URL
2. Render a `FileViewer` component with the returned `path`
3. Use `surface_id="file-content"`:

```json
emit_ui(
  surface_id="file-content",
  components=[
    {
      "id": "root",
      "type": "FileViewer",
      "props": {
        "path": "Sales & Pipeline/Q1_Pipeline_Report.md",
        "filename": "Q1_Pipeline_Report.md",
        "preview_type": "text",
        "raw_url": "/api/files/Sales%20%26%20Pipeline/Q1_Pipeline_Report.md/raw",
        "viewer": {
          "kind": "text",
          "raw_url": "/api/files/Sales%20%26%20Pipeline/Q1_Pipeline_Report.md/raw"
        }
      },
      "children": []
    }
  ],
  grid={"w": 8, "h": 7}
)
```
This component loads the full raw file. Do not replace it with preview bullets or summaries.

#### Example: File Search Surface
When the user asks "find files about X" or "what do I have on pricing":
1. Call `search_user_files(query)` 
2. Render matching files with their domain tags and a brief summary snippet
