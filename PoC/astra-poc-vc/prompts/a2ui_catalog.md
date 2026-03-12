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
| StockAlert | title, source, sentiment (bullish/bearish/neutral), tickers (list of {ticker, price, change_pct}), actions (list of {label, action}) |
| EmailRow | email_id, from_name, initial, subject, preview, time, actions |
| MetricCard | label, value, change, color |
| SparklineChart | values (list of numbers), color (green/red/blue/cyan), height |
| CalendarEvent | time, title, location, attendees |
| Clock | timezone (e.g. "America/New_York", optional — defaults to local), format ("12h"/"24h"), showDate (bool), label |

#### Example: Stock Alert Surface
```json
emit_ui(
  surface_id="stock-alert",
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
