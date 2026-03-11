### Widget Template System (Generative UI)

Use these pre-built interactive component patterns for consistent, rich widgets. Widgets run inside iframes with access to `dispatchAgentEvent(eventName, payload)` to communicate back to the agent.

#### SHARED CSS (include at top of every widget inside a `<style>` tag):
```css
* { box-sizing: border-box; margin: 0; padding: 0; }
:root {
  --bg-panel: rgba(26, 29, 36, 0.85);
  --bg-card: rgba(15, 17, 21, 0.6);
  --bg-hover: rgba(255, 255, 255, 0.06);
  --bg-active: rgba(59, 130, 246, 0.15);
  --border: rgba(255, 255, 255, 0.08);
  --text-primary: #f8fafc;
  --text-secondary: #94a3b8;
  --text-muted: #64748b;
  --accent-blue: #3b82f6;
  --accent-cyan: #06b6d4;
  --accent-green: #10b981;
  --accent-amber: #f59e0b;
  --accent-red: #ef4444;
  --radius: 12px;
  --radius-sm: 8px;
}
body { background: transparent; }
```

#### INTERACTIVITY BRIDGE:
Widgets can send events back to the agent using:
```js
dispatchAgentEvent('event_name', { key: 'value' });
```
Examples:
- `dispatchAgentEvent('stock_clicked', { ticker: 'AAPL' })` — user clicks a stock
- `dispatchAgentEvent('email_clicked', { id: '3' })` — user clicks an email
- `dispatchAgentEvent('action_requested', { action: 'draft_reply', email_id: '5' })` — user clicks "Reply"
- `dispatchAgentEvent('tab_changed', { tab: 'watchlist' })` — user switches tab
- `dispatchAgentEvent('refresh_requested', { widget: 'stock-alert' })` — user clicks refresh

#### COMPONENT: Tab Bar (Interactive)
```html
<div class="tab-bar" style="display:flex; gap:2px; background:var(--bg-card); border-radius:var(--radius-sm); padding:3px; margin-bottom:12px;">
  <button class="tab active" onclick="switchTab(this,'tab1')" style="flex:1; padding:8px 12px; border:none; border-radius:6px; background:var(--accent-blue); color:var(--text-primary); font-size:12px; font-weight:600; cursor:pointer; font-family:inherit; transition:all 0.2s;">Tab 1</button>
  <button class="tab" onclick="switchTab(this,'tab2')" style="flex:1; padding:8px 12px; border:none; border-radius:6px; background:transparent; color:var(--text-secondary); font-size:12px; font-weight:500; cursor:pointer; font-family:inherit; transition:all 0.2s;">Tab 2</button>
</div>
<div id="tab1" class="tab-content" style="display:block;"><!-- content --></div>
<div id="tab2" class="tab-content" style="display:none;"><!-- content --></div>
<script>
function switchTab(btn, tabId) {
  document.querySelectorAll('.tab').forEach(t => { t.style.background='transparent'; t.style.color='var(--text-secondary)'; t.style.fontWeight='500'; });
  btn.style.background='var(--accent-blue)'; btn.style.color='var(--text-primary)'; btn.style.fontWeight='600';
  document.querySelectorAll('.tab-content').forEach(c => c.style.display='none');
  document.getElementById(tabId).style.display='block';
  dispatchAgentEvent('tab_changed', { tab: tabId });
}
</script>
```

#### COMPONENT: Expandable Section (Accordion)
```html
<div class="accordion" style="border:1px solid var(--border); border-radius:var(--radius-sm); overflow:hidden; margin-bottom:8px;">
  <div onclick="toggleAccordion(this)" style="display:flex; align-items:center; justify-content:space-between; padding:12px 14px; cursor:pointer; background:var(--bg-card); transition:background 0.15s;" onmouseover="this.style.background='var(--bg-hover)'" onmouseout="this.style.background='var(--bg-card)'">
    <span style="color:var(--text-primary); font-size:13px; font-weight:600;">Section Title</span>
    <span class="chevron" style="color:var(--text-muted); transition:transform 0.2s; font-size:10px;">▼</span>
  </div>
  <div class="accordion-body" style="max-height:0; overflow:hidden; transition:max-height 0.3s ease; padding:0 14px;">
    <div style="padding:12px 0;"><!-- content --></div>
  </div>
</div>
<script>
function toggleAccordion(header) {
  const body = header.nextElementSibling;
  const chevron = header.querySelector('.chevron');
  if (body.style.maxHeight === '0px' || !body.style.maxHeight) {
    body.style.maxHeight = body.scrollHeight + 'px'; body.style.padding = '0 14px';
    chevron.style.transform = 'rotate(180deg)';
  } else {
    body.style.maxHeight = '0px';
    chevron.style.transform = 'rotate(0deg)';
  }
}
</script>
```

#### COMPONENT: Notification Banner (with dismiss)
```html
<div id="notif-ID" style="background:linear-gradient(135deg, rgba(ACCENT_RGB,0.15), transparent); border:1px solid rgba(ACCENT_RGB,0.3); border-radius:var(--radius-sm); padding:12px 16px; display:flex; align-items:center; gap:12px; animation:slideIn 0.3s ease;">
  <span style="font-size:20px;">EMOJI</span>
  <div style="flex:1;">
    <div style="color:var(--text-primary); font-weight:600; font-size:14px;">TITLE</div>
    <div style="color:var(--text-secondary); font-size:12px;">SUBTITLE</div>
  </div>
  <button onclick="this.parentElement.style.display='none'" style="background:none; border:none; color:var(--text-muted); cursor:pointer; font-size:16px; padding:4px;">✕</button>
</div>
<style>@keyframes slideIn { from { opacity:0; transform:translateY(-8px); } to { opacity:1; transform:translateY(0); } }</style>
```
Use ACCENT_RGB: `59,130,246` (blue), `245,158,11` (amber/bullish), `239,68,68` (red/bearish), `16,185,129` (green), `6,182,212` (cyan/travel).

#### COMPONENT: Metric Card (clickable)
```html
<div onclick="dispatchAgentEvent('metric_clicked',{metric:'METRIC_KEY'})" style="background:var(--bg-card); border:1px solid var(--border); border-radius:var(--radius); padding:16px; cursor:pointer; transition:all 0.2s; min-width:140px;" onmouseover="this.style.borderColor='var(--accent-blue)'; this.style.transform='translateY(-2px)'" onmouseout="this.style.borderColor='var(--border)'; this.style.transform='none'">
  <div style="color:var(--text-muted); font-size:11px; text-transform:uppercase; letter-spacing:0.5px;">LABEL</div>
  <div style="color:var(--text-primary); font-size:24px; font-weight:700; margin:4px 0;">VALUE</div>
  <div style="color:var(--accent-COLOR); font-size:13px; font-weight:500;">CHANGE</div>
</div>
```


#### COMPONENT: Stock Ticker Row (interactive)
```html
<div onclick="dispatchAgentEvent('stock_clicked',{ticker:'TICKER'})" style="display:flex; align-items:center; gap:12px; padding:10px 12px; border-radius:var(--radius-sm); background:var(--bg-card); border:1px solid var(--border); cursor:pointer; transition:all 0.15s;" onmouseover="this.style.borderColor='var(--accent-blue)'; this.style.background='var(--bg-hover)'" onmouseout="this.style.borderColor='var(--border)'; this.style.background='var(--bg-card)'">
  <div style="font-weight:700; color:var(--text-primary); font-size:14px; width:60px;">TICKER</div>
  <div style="flex:1; color:var(--text-secondary); font-size:12px;">COMPANY</div>
  <div style="text-align:right;">
    <div style="color:var(--text-primary); font-weight:600; font-size:14px;">$PRICE</div>
    <div style="color:var(--accent-COLOR); font-size:12px; font-weight:500;">CHANGE%</div>
  </div>
</div>
```
When user clicks a stock, the agent receives `stock_clicked` event and can show detailed info, chart, or analysis.

#### COMPONENT: Email Row (interactive with actions)
```html
<div style="display:flex; align-items:center; gap:12px; padding:10px 12px; border-radius:var(--radius-sm); transition:background 0.15s; cursor:pointer;" onmouseover="this.style.background='var(--bg-hover)'; this.querySelector('.actions').style.opacity='1'" onmouseout="this.style.background='transparent'; this.querySelector('.actions').style.opacity='0'" onclick="dispatchAgentEvent('email_clicked',{id:'EMAIL_ID'})">
  <div style="width:36px; height:36px; border-radius:50%; background:var(--accent-blue); display:flex; align-items:center; justify-content:center; font-size:14px; flex-shrink:0; color:white;">INITIAL</div>
  <div style="flex:1; min-width:0;">
    <div style="color:var(--text-primary); font-size:13px; font-weight:500; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">SUBJECT</div>
    <div style="color:var(--text-secondary); font-size:12px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">FROM — PREVIEW</div>
  </div>
  <div class="actions" style="display:flex; gap:6px; opacity:0; transition:opacity 0.15s;">
    <button onclick="event.stopPropagation(); dispatchAgentEvent('action_requested',{action:'reply',email_id:'EMAIL_ID'})" style="background:var(--accent-blue); border:none; color:white; border-radius:6px; padding:4px 10px; font-size:11px; cursor:pointer; font-family:inherit;">Reply</button>
    <button onclick="event.stopPropagation(); dispatchAgentEvent('action_requested',{action:'summarize',email_id:'EMAIL_ID'})" style="background:var(--bg-card); border:1px solid var(--border); color:var(--text-secondary); border-radius:6px; padding:4px 10px; font-size:11px; cursor:pointer; font-family:inherit;">Summarize</button>
  </div>
  <div style="color:var(--text-muted); font-size:11px; flex-shrink:0;">TIME</div>
</div>
```

#### COMPONENT: Action Button Row
```html
<div style="display:flex; gap:8px; margin-top:12px;">
  <button onclick="dispatchAgentEvent('action_requested',{action:'ACTION1'})" style="flex:1; padding:10px; background:var(--accent-blue); border:none; border-radius:var(--radius-sm); color:white; font-size:13px; font-weight:600; cursor:pointer; font-family:inherit; transition:all 0.2s;" onmouseover="this.style.transform='translateY(-1px)'; this.style.boxShadow='0 4px 12px rgba(59,130,246,0.3)'" onmouseout="this.style.transform='none'; this.style.boxShadow='none'">Button 1</button>
  <button onclick="dispatchAgentEvent('action_requested',{action:'ACTION2'})" style="flex:1; padding:10px; background:var(--bg-card); border:1px solid var(--border); border-radius:var(--radius-sm); color:var(--text-secondary); font-size:13px; font-weight:500; cursor:pointer; font-family:inherit; transition:all 0.2s;" onmouseover="this.style.borderColor='var(--accent-blue)'" onmouseout="this.style.borderColor='var(--border)'">Button 2</button>
</div>
```

#### COMPONENT: Mini Sparkline Chart (CSS-only)
For showing stock price trends without external libraries:
```html
<div style="display:flex; align-items:end; gap:2px; height:40px; padding:4px 0;">
  <!-- Generate bars from data, each bar is a div -->
  <div style="flex:1; background:var(--accent-COLOR); border-radius:2px 2px 0 0; height:60%; opacity:0.6;"></div>
  <div style="flex:1; background:var(--accent-COLOR); border-radius:2px 2px 0 0; height:75%; opacity:0.7;"></div>
  <div style="flex:1; background:var(--accent-COLOR); border-radius:2px 2px 0 0; height:50%; opacity:0.6;"></div>
  <div style="flex:1; background:var(--accent-COLOR); border-radius:2px 2px 0 0; height:85%; opacity:0.8;"></div>
  <div style="flex:1; background:var(--accent-COLOR); border-radius:2px 2px 0 0; height:100%; opacity:1;"></div>
  <!-- Last bar is current price, tallest if trending up -->
</div>
```
Scale bar heights proportionally to actual price data. Use green for uptrend, red for downtrend.

#### COMPONENT: Progress/Gauge
```html
<div style="background:var(--bg-card); border-radius:99px; height:6px; overflow:hidden; margin:8px 0;">
  <div style="background:linear-gradient(90deg, var(--accent-blue), var(--accent-cyan)); height:100%; width:PERCENT%; border-radius:99px; transition:width 0.5s ease;"></div>
</div>
```

#### COMPONENT: Tooltip on Hover
```html
<span style="position:relative; cursor:help;" onmouseover="this.querySelector('.tooltip').style.opacity='1'; this.querySelector('.tooltip').style.transform='translateY(0)'" onmouseout="this.querySelector('.tooltip').style.opacity='0'; this.querySelector('.tooltip').style.transform='translateY(4px)'">
  TRIGGER_TEXT
  <span class="tooltip" style="position:absolute; bottom:calc(100% + 6px); left:50%; transform:translateX(-50%) translateY(4px); background:var(--bg-panel); border:1px solid var(--border); border-radius:6px; padding:6px 10px; font-size:11px; color:var(--text-secondary); white-space:nowrap; opacity:0; transition:all 0.2s; pointer-events:none; z-index:10;">TOOLTIP_TEXT</span>
</span>
```

#### LAYOUT: Dashboard Grid
```html
<div style="width:100%; height:100%; display:flex; flex-direction:column; font-family:'Inter',system-ui,sans-serif; padding:16px; gap:12px; overflow-y:auto;">
  <!-- Notification banner (if alert) -->
  <!-- Tab bar (if multiple views) -->
  <!-- Metric cards grid -->
  <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(160px, 1fr)); gap:10px;">
    <!-- Metric cards -->
  </div>
  <!-- List sections -->
  <div style="background:var(--bg-panel); backdrop-filter:blur(12px); border:1px solid var(--border); border-radius:var(--radius); padding:14px;">
    <!-- Section header + interactive rows -->
  </div>
  <!-- Action buttons -->
</div>
```

#### RULES:
1. ALWAYS include the shared CSS in a `<style>` tag at the top of every widget
2. ALWAYS use CSS variables — never hardcode colors
3. ALWAYS add hover states and transitions for interactive elements
4. ALWAYS use `dispatchAgentEvent()` for clickable items so the agent can respond
5. Use Tab Bar when widget has multiple views (e.g., "Inbox" / "Watchlist" / "Calendar")
6. Use Expandable Sections for detailed content that should be collapsed by default
7. Use Action Buttons for things the agent can do (Reply, Summarize, Refresh, Buy/Sell)
8. Add dismiss buttons (✕) on notification banners
9. Show hover actions on email/data rows (Reply, Summarize appear on hover)
10. Use Mini Sparkline Charts for stock price trends
11. Add `animation: slideIn 0.3s ease` for new notifications
12. Keep font sizes consistent: 11px muted, 12px secondary, 13px body, 14px titles, 24px hero numbers
13. Use amber accent for bullish, red for bearish, green for positive, cyan for travel, blue for default
