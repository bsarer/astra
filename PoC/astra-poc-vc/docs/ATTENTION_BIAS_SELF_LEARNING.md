# AstraOS — Attention, Bias & Self-Learning Architecture

## The Attention Frame Problem

You are one person with one attention span, staring at a vast data space — emails, files, calendar, stocks, conversations, everything you've ever touched. You can only hold one frame at a time. You miss things. You forget things. You're biased toward whatever's loudest or most recent. The important thing that needed your attention three hours ago? It's buried under noise. The connection between Tuesday's email and Thursday's meeting? You'll only see it if you're lucky.

This is the fundamental bottleneck of knowledge work. Not the data. Not the tools. Your attention.

Now imagine you could split yourself. Not copies — versions. A version of you that watches your finances with a trader's instinct. Another that tracks your client relationships with the memory of a decade-long executive assistant. Another that monitors your calendar, your deadlines, your commitments — and knows which ones you'll forget. Each version has its own biased attention frame, tuned to notice different signals in the same data space.

That's what this architecture does. Each domain is a separate attention frame pointed at the same underlying reality. Finance, sales, travel, team — each with its own bias, its own memory of what you cared about, its own sense of what's urgent right now. When you ask a question, the right frame steps forward with the right context already in focus.

And like real attention, these frames learn. The finance frame notices you keep dismissing TSLA alerts — it dials down. The sales frame notices you always open the pricing doc before Acme meetings — it starts surfacing it before you ask. The travel frame notices you never check weather until the day before — it waits.

You are one person. The system gives you the attention span of many — each one learning, each one biased in a useful way, each one watching a part of your world so you don't have to.

The philosophy: the system should work the way your mind works — absorb, filter, decide, learn — but without the limits of one brain, one focus, one frame at a time.

## The Heartbeat: How Attention Frames Come Alive

The Heartbeat is the central loop that runs continuously — the pulse of the system. Every tick, it cycles through all active attention frames, checks what each one sees, and decides: inform the user, take action, or stay quiet.

### Concrete Example: Friday Evening, Mike's Heartbeat Fires

```
┌─────────────────────────────────────────────────────────────────┐
│                     HEARTBEAT (runs every 2 min)                │
│                                                                 │
│  tick #147 — Friday 5:45 PM                                     │
│                                                                 │
│  ┌─ Personal Frame ────────────────────────────────────────┐    │
│  │                                                         │    │
│  │  SIGNAL: Calendar event tonight — "Stand-up Comedy @    │    │
│  │  The Creek and The Cave, 8:00 PM"                       │    │
│  │                                                         │    │
│  │  KNOWLEDGE GRAPH TRAVERSAL:                             │    │
│  │    event: Stand-up Comedy                               │    │
│  │      → located_in: The Creek and The Cave, LIC          │    │
│  │      → performer: Sam Morril (from Ticketmaster email)  │    │
│  │      → Mike's preference: comedy = high engagement      │    │
│  │        (attended 3 shows in last 2 months)              │    │
│  │                                                         │    │
│  │  ATTENTION SCORE: 0.92 (high — event in 2h15m,         │    │
│  │    strong personal preference, Friday evening)          │    │
│  │                                                         │    │
│  │  DECISION: → INFORM + ACT                               │    │
│  │                                                         │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                 │
│  ┌─ Travel Frame ──────────────────────────────────────────┐    │
│  │                                                         │    │
│  │  TRIGGERED BY: Personal frame flagged a location event  │    │
│  │                                                         │    │
│  │  KNOWLEDGE GRAPH TRAVERSAL:                             │    │
│  │    location: The Creek and The Cave                     │    │
│  │      → address: 10-93 Jackson Ave, LIC, Queens          │    │
│  │    Mike's location: Austin, TX... wait — Mike is in     │    │
│  │      NYC this week (from travel frame memory:           │    │
│  │      "NYC trip, hotel in Midtown")                      │    │
│  │                                                         │    │
│  │  ROUTE LOOKUP:                                          │    │
│  │    Midtown → LIC: 7 train to Vernon-Jackson, 25 min    │    │
│  │    Leave by 7:15 PM to arrive with buffer               │    │
│  │                                                         │    │
│  │  ATTENTION SCORE: 0.88 (high — supports active event)   │    │
│  │                                                         │    │
│  │  DECISION: → ENRICH the personal frame's output         │    │
│  │                                                         │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                 │
│  ┌─ Finance Frame ─────────────────────────────────────────┐    │
│  │  ATTENTION SCORE: 0.12 (low — Friday evening, markets   │    │
│  │  closed, no urgent signals)                             │    │
│  │  DECISION: → STAY QUIET                                 │    │
│  │                                                         │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                 │
│  ┌─ Sales Frame ───────────────────────────────────────────┐    │
│  │  ATTENTION SCORE: 0.08 (low — weekend, no meetings)     │    │
│  │  DECISION: → STAY QUIET                                 │    │
│  │                                                         │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                 │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                    ACTION ORCHESTRATOR                           │
│                                                                 │
│  Inputs from frames:                                            │
│    • Personal: event tonight, high attention, performer known   │
│    • Travel: route calculated, departure time set               │
│    • Finance: quiet                                             │
│    • Sales: quiet                                               │
│                                                                 │
│  Action plan:                                                   │
│                                                                 │
│  1. EMIT UI — evening briefing widget                           │
│     surface_id: "tonight-plan"                                  │
│     components:                                                 │
│       Card: "Tonight: Stand-up Comedy"                          │
│       Text: "Sam Morril @ The Creek and The Cave"               │
│       Text: "8:00 PM — Doors at 7:30"                           │
│       Divider                                                   │
│       Text: "🚇 Take the 7 train to Vernon-Jackson"             │
│       Text: "Leave by 7:15 from Midtown — 25 min ride"          │
│       MetricCard: "Depart in 1h 30m"                            │
│       Button: "Set reminder at 7:00 PM"                         │
│       Button: "Show me Sam Morril's clips"                      │
│                                                                 │
│  2. GENERATE VIDEO (async, via AI video-gen)                    │
│     prompt: "Quick visual guide: walking from Midtown hotel     │
│     to 7 train platform, riding to Vernon-Jackson, walking      │
│     to The Creek and The Cave on Jackson Ave. Evening vibe,     │
│     NYC streets, comedy club entrance."                         │
│     → renders as a short clip in the widget when ready          │
│                                                                 │
│  3. SET REMINDER — 7:00 PM push notification                    │
│     "Time to head out — 7 train to Vernon-Jackson, 25 min"     │
│                                                                 │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                    USER SEES                                     │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  🎭 Tonight: Stand-up Comedy                              │  │
│  │                                                           │  │
│  │  Sam Morril @ The Creek and The Cave                      │  │
│  │  8:00 PM — Doors at 7:30                                  │  │
│  │  ─────────────────────────────────                        │  │
│  │  🚇 Take the 7 train to Vernon-Jackson                    │  │
│  │  Leave by 7:15 from Midtown — 25 min ride                 │  │
│  │                                                           │  │
│  │  ┌─────────────┐                                          │  │
│  │  │ Depart in   │                                          │  │
│  │  │  1h 30m     │                                          │  │
│  │  └─────────────┘                                          │  │
│  │                                                           │  │
│  │  ▶ [AI-generated route video loading...]                   │  │
│  │                                                           │  │
│  │  [Set reminder 7:00 PM]  [Sam Morril clips]               │  │
│  │                                                           │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                 │
│  Mike didn't ask for any of this.                               │
│  The heartbeat noticed. The frames connected the dots.          │
│  The system acted.                                              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Heartbeat Flow (Generalized)

```
Every N minutes (configurable, default 2 min):
        │
        ▼
┌─ HEARTBEAT TICK ────────────────────────────────────────────┐
│                                                             │
│  For each attention frame (personal, finance, sales,        │
│  travel, team):                                             │
│                                                             │
│    1. SCAN — check knowledge graph for time-sensitive       │
│       entities (events, deadlines, reminders)               │
│                                                             │
│    2. SCORE — compute attention score:                      │
│       temporal × interaction_history × preference_weight    │
│                                                             │
│    3. DECIDE:                                               │
│       score < 0.3  → STAY QUIET (nothing worth surfacing)  │
│       score 0.3-0.7 → INFORM (show widget, no action)      │
│       score > 0.7  → INFORM + ACT (widget + take action)   │
│                                                             │
│    4. CROSS-FRAME CHECK — does this frame's signal          │
│       trigger another frame?                                │
│       (personal event → triggers travel frame for route)    │
│       (sales deadline → triggers team frame for prep)       │
│                                                             │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─ ACTION ORCHESTRATOR ───────────────────────────────────────┐
│                                                             │
│  Collect all frame outputs with score > 0.3                 │
│  Merge cross-frame enrichments                              │
│  Deduplicate (don't show same entity twice)                 │
│                                                             │
│  For each actionable item:                                  │
│                                                             │
│    → emit_ui: render widget with context                    │
│    → generate_video: async AI video-gen for visual guides   │
│    → set_reminder: schedule future notification             │
│    → send_message: draft email/message for user review      │
│    → book_action: reserve, RSVP, etc (with user approval)  │
│                                                             │
│  Inject as [SYSTEM] message into agent conversation         │
│  → triggers existing agent pipeline                         │
│  → agent renders via emit_ui                                │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Self-Learning After Heartbeat Actions

```
After each heartbeat-triggered action:
        │
        ▼
┌─ FEEDBACK LOOP ─────────────────────────────────────────────┐
│                                                             │
│  User engaged (clicked, asked follow-up)?                   │
│    → boost that frame's preference weight                   │
│    → boost that entity's attention score                    │
│    → store: "proactive comedy suggestion → engaged"         │
│                                                             │
│  User dismissed?                                            │
│    → reduce frame's proactive threshold                     │
│    → store: "proactive comedy suggestion → dismissed"       │
│    → next time, require higher score to surface             │
│                                                             │
│  User ignored (no interaction for 10 min)?                  │
│    → gentle decay on that signal type                       │
│    → maybe the timing was wrong, not the content            │
│                                                             │
│  User said "this was great" / "don't do this again"?        │
│    → explicit signal, strongest weight adjustment           │
│    → stored as opinion with high confidence                 │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

Inspired by:
- [Nate's Newsletter: You built an AI memory system. Now your agent needs hands.](https://natesnewsletter.substack.com/p/you-built-an-ai-memory-system-now)
- [Yogesh Yadav: AI Agent Memory Systems in 2026](https://yogeshyadav.medium.com/ai-agent-memory-systems-in-2026-mem0-zep-hindsight-memvid-and-everything-in-between-compared-96e35b818da8)

Key takeaways from the research:
- Hindsight's 4-network architecture (World, Experience, Opinion, Entity) separates facts from beliefs — this is critical for bias management
- The "two-door principle" from Open Brain: agent and human see the same data, both read and write — transparency kills black-box bias
- Memory as cognitive substrate, not storage — the system should maintain the distinction between facts and beliefs, track how knowledge changes over time, and explain its reasoning
- Mem0's CRUD operations on memories (ADD, UPDATE, DELETE, NOOP) solve belief contradiction — when a user changes their mind, the old belief gets replaced, not appended

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        USER INTERACTION                             │
│   clicks, dismissals, dwell time, follow-ups, explicit feedback     │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     ATTENTION MANAGER                                │
│                                                                     │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────────────────┐ │
│  │  Temporal    │  │  Interaction │  │  Salience                  │ │
│  │  Scorer      │  │  Tracker     │  │  Ranker                    │ │
│  │             │  │              │  │                            │ │
│  │ "what's     │  │ "what did    │  │ "what SHOULD the user      │ │
│  │  happening  │  │  the user    │  │  care about right now?"    │ │
│  │  soon?"     │  │  engage      │  │                            │ │
│  │             │  │  with?"      │  │  combines temporal +       │ │
│  │ events,     │  │              │  │  interaction + domain      │ │
│  │ deadlines,  │  │ views,       │  │  signals into a single     │ │
│  │ reminders   │  │ clicks,      │  │  attention score per       │ │
│  │             │  │ dismissals,  │  │  entity                    │ │
│  │             │  │ dwell time   │  │                            │ │
│  └──────┬──────┘  └──────┬───────┘  └─────────────┬──────────────┘ │
│         │                │                         │                │
│         └────────────────┴─────────────────────────┘                │
│                          │                                          │
│                   attention_score                                    │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      BIAS DETECTOR                                   │
│                                                                     │
│  Monitors retrieval patterns and flags imbalances:                  │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ Recency Bias    — are we always showing the newest thing?   │   │
│  │ Domain Bias     — 80% finance context when user is 50/50?  │   │
│  │ Frequency Bias  — same entity keeps appearing, user ignores │   │
│  │ Confirmation    — only surfacing data that agrees with      │   │
│  │   Bias            the last decision?                        │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  Output: bias_adjustments (per-domain, per-entity weight tweaks)    │
│                                                                     │
│  Two modes:                                                         │
│    WITHOUT MODEL — rule-based counters and thresholds               │
│    WITH MODEL    — periodic LLM reflection on retrieval patterns    │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    BELIEF NETWORK                                     │
│            (inspired by Hindsight's 4-network model)                │
│                                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐  │
│  │ Facts        │  │ Opinions     │  │ Experiences              │  │
│  │              │  │              │  │                          │  │
│  │ "Tom works   │  │ "Mike prefers│  │ "Last time we showed     │  │
│  │  at Acme"    │  │  stocks in   │  │  a stock alert, Mike     │  │
│  │              │  │  the morning"│  │  clicked through and     │  │
│  │ immutable    │  │              │  │  asked for more detail"  │  │
│  │ until        │  │ confidence:  │  │                          │  │
│  │ contradicted │  │ 0.0 → 1.0   │  │ first-person agent       │  │
│  │              │  │              │  │ action history           │  │
│  │ source:      │  │ updates with │  │                          │  │
│  │ extracted    │  │ evidence     │  │ source: interaction      │  │
│  │ from data    │  │              │  │ tracker                  │  │
│  └──────────────┘  └──────────────┘  └──────────────────────────┘  │
│                                                                     │
│  Key: opinions have confidence scores that decay or strengthen      │
│  based on evidence. Facts get REPLACED when contradicted (Mem0      │
│  style ADD/UPDATE/DELETE), not appended.                            │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    SELF-LEARNING LOOP                                 │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                                                              │   │
│  │   1. OBSERVE — track what was surfaced vs what was used      │   │
│  │                                                              │   │
│  │   2. MEASURE — was the context helpful?                      │   │
│  │      • user engaged → positive signal                        │   │
│  │      • user dismissed → negative signal                      │   │
│  │      • user ignored → weak negative                          │   │
│  │      • user asked for something we didn't surface → miss     │   │
│  │                                                              │   │
│  │   3. ADJUST — update weights                                 │   │
│  │      WITHOUT MODEL:                                          │   │
│  │        • increment/decrement attention scores                │   │
│  │        • adjust domain preference weights                    │   │
│  │        • update opinion confidence in belief network          │   │
│  │        • apply bias corrections                              │   │
│  │                                                              │   │
│  │      WITH MODEL (periodic, async):                           │   │
│  │        • "review last 20 interactions — what patterns        │   │
│  │           do you see? what should we surface more/less?"     │   │
│  │        • LLM generates adjustment recommendations           │   │
│  │        • human-reviewable before applying                    │   │
│  │                                                              │   │
│  │   4. PERSIST — store adjustments as preference memories      │   │
│  │                                                              │   │
│  └──────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

## Flow Diagram: Per-Turn Context Assembly

```
User message arrives
        │
        ▼
┌─ Domain Router ─────────────────────────────┐
│  classify intent → [finance, sales, ...]    │
└──────────────────────┬──────────────────────┘
                       │
        ┌──────────────┼──────────────────┐
        ▼              ▼                  ▼
   Memory          Knowledge         Attention
   Manager         Graph              Manager
   (existing)      (new)             (new)
        │              │                  │
        │  top-5       │  traverse        │  score each
        │  memories    │  entities        │  result by
        │  by domain   │  + relations     │  temporal +
        │              │                  │  interaction +
        │              │                  │  preference
        └──────────────┼──────────────────┘
                       │
                       ▼
              ┌─ Bias Detector ─┐
              │  check for      │
              │  domain skew,   │
              │  recency bias,  │
              │  frequency bias │
              │                 │
              │  apply          │
              │  corrections    │
              └────────┬────────┘
                       │
                       ▼
              ┌─ Context Budget ─┐
              │  800 tokens max  │
              │                  │
              │  400 = memories  │
              │  400 = graph +   │
              │        attention │
              │                  │
              │  deduplicate     │
              │  rank by final   │
              │  attention score │
              └────────┬─────────┘
                       │
                       ▼
              Inject into system prompt
                       │
                       ▼
              LLM reasons + responds
                       │
                       ▼
        ┌──────────────┼──────────────────┐
        ▼              ▼                  ▼
   Render UI      Extract          Self-Learning
   (emit_ui)      entities +       Loop
                  facts            (observe →
                  (async)          measure →
                                   adjust →
                                   persist)
```

## Flow Diagram: Self-Learning Without Model

```
Every interaction:
        │
        ▼
┌─ Interaction Tracker ───────────────────────┐
│                                             │
│  Event: widget_rendered(stock-watchlist)     │
│  Event: user_clicked(stock-watchlist, NVDA)  │
│  Event: user_dismissed(travel-prep)          │
│  Event: user_ignored(meeting-reminder, 5min) │
│  Event: user_asked("show me acme pricing")   │
│    → was acme pricing in context? NO → miss  │
│                                             │
└──────────────────────┬──────────────────────┘
                       │
                       ▼
┌─ Rule-Based Adjustments ────────────────────┐
│                                             │
│  clicked → entity.access_count += 1         │
│            domain.preference_weight += 0.05 │
│            opinion.confidence += 0.1        │
│                                             │
│  dismissed → entity.access_count -= 0       │
│              domain.preference_weight -= 0.03│
│              opinion.confidence -= 0.15     │
│              suppress entity this session   │
│                                             │
│  ignored → domain.preference_weight -= 0.01 │
│            (gentle decay)                   │
│                                             │
│  miss → log as "context_miss" memory        │
│         boost related entity attention      │
│         next retrieval includes it          │
│                                             │
│  Bias check:                                │
│    if domain_X > 70% of last 20 retrievals  │
│    AND user engagement with domain_X < 50%  │
│    → reduce domain_X weight by 0.1          │
│    → boost underrepresented domains by 0.05 │
│                                             │
└──────────────────────┬──────────────────────┘
                       │
                       ▼
              Store as preference memories
              (type=fact, tag=preference_signal)
              in existing Qdrant memories collection
```

## Flow Diagram: Self-Learning With Model (Periodic Reflection)

```
Every N interactions (e.g., 20) or end of session:
        │
        ▼
┌─ Collect Reflection Data ───────────────────┐
│                                             │
│  • Last 20 context injections               │
│  • What was surfaced vs what was used       │
│  • Engagement/dismissal/ignore counts       │
│  • Context misses (user asked for X,        │
│    X wasn't in context)                     │
│  • Current belief network state             │
│  • Current domain preference weights        │
│                                             │
└──────────────────────┬──────────────────────┘
                       │
                       ▼
┌─ LLM Reflection Call ──────────────────────────────────────┐
│                                                            │
│  Prompt:                                                   │
│  "You are reviewing the attention and memory system for    │
│   a personal AI assistant. Here are the last 20            │
│   interactions:                                            │
│                                                            │
│   [interaction_log]                                        │
│                                                            │
│   Current beliefs:                                         │
│   [belief_network_snapshot]                                │
│                                                            │
│   Questions:                                               │
│   1. Which opinions should increase/decrease confidence?   │
│   2. Are there new opinions to form?                       │
│   3. Any domain biases to correct?                         │
│   4. What context misses should we prevent next time?      │
│   5. Any entities to promote or demote in attention?"      │
│                                                            │
│  Output: structured JSON with adjustments                  │
│                                                            │
└──────────────────────┬─────────────────────────────────────┘
                       │
                       ▼
┌─ Apply or Review ───────────────────────────┐
│                                             │
│  Low-confidence adjustments → apply auto    │
│  High-impact adjustments → surface to user: │
│                                             │
│  "I noticed you've been dismissing stock    │
│   alerts lately. Want me to reduce their    │
│   priority?"                                │
│                                             │
│  User confirms → apply                      │
│  User rejects → store as evidence           │
│                                             │
└─────────────────────────────────────────────┘
```

## The Two-Door Principle (from Open Brain)

Every piece of data in the system has two doors:
- The agent door: the agent reads, writes, and reasons over it
- The human door: the user sees the same data, can inspect it, correct it, override it

Applied to AstraOS:

| Data | Agent Door | Human Door |
|------|-----------|------------|
| Knowledge Graph | Traverses entities, injects context | "Show me what you know about Acme" → renders graph view widget |
| Belief Network | Uses opinions to rank context | "What do you think I care about?" → shows beliefs with confidence scores |
| Attention Scores | Ranks what to surface | "Why did you show me this?" → explains the attention score breakdown |
| Bias Corrections | Auto-adjusts retrieval weights | "You've been showing me a lot of stock stuff" → user can manually adjust |
| Context Misses | Logs and learns from gaps | "You should have shown me the pricing doc" → user teaches the system |

This is the transparency layer. The user is never wondering "why did it show me that?" — they can always ask, and the system can always explain.

## Mapping to Existing AstraOS Components

| New Component | Builds On | Where It Lives |
|--------------|-----------|----------------|
| Attention Manager | `domain_router.py` + `memory.py` temporal scoring | `attention.py` (new) |
| Bias Detector | Domain preference weights in `memory.py` | `attention.py` (new, same module) |
| Belief Network | `memory.py` memory types (fact, episode) | Extends `memory.py` with opinion type + confidence field |
| Interaction Tracker | Dashboard `handleAction` + `removeWindow` callbacks | `main.py` new endpoints + frontend event emitters |
| Self-Learning Loop (no model) | `memory_extract_node` in `agent.py` | Extends `memory_extract_node` |
| Self-Learning Loop (with model) | Periodic task like `email_poller` | `reflection.py` (new) |
| Two-Door UI | `emit_ui` + A2UI components | New components: BeliefView, AttentionDebug, GraphExplorer |

## Implementation Priority

1. Interaction Tracker — start collecting signals (clicks, dismissals, ignores) immediately. No model needed. Just event logging.
2. Attention Manager — temporal + interaction scoring. Rule-based. Replaces the current flat `access_count` with a real attention score.
3. Belief Network — extend memory types with `opinion` + confidence. Mem0-style CRUD (update/delete old beliefs, don't just append).
4. Bias Detector — rule-based counters first. Flag when domain distribution doesn't match engagement distribution.
5. Self-Learning Loop (no model) — wire interaction signals to weight adjustments. Fully programmatic.
6. Two-Door UI — build the transparency widgets so the user can inspect and correct.
7. Self-Learning Loop (with model) — periodic LLM reflection. Last priority because it burns tokens and the rule-based loop handles 80% of cases.

## Philosophy (one sentence)

The system should remember not just what you said, but what you saw, what you ignored, and what you needed but didn't ask for — then get better at knowing the difference.

## Technology Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| Knowledge Graph | Qdrant (payload-based edges) | Already in stack, filtered vector search + structured payloads for relationships |
| Belief Network | Qdrant `memories` collection + `opinion` type with confidence | Extends existing memory, no new DB |
| Attention Scoring | Pure Python, rule-based | Temporal decay, interaction counters, domain weights. Fast, deterministic, free |
| Bias Detection | Pure Python, statistical counters | Domain distribution vs engagement distribution. Threshold flags. Zero tokens |
| Interaction Tracking | FastAPI endpoints + frontend event emitters | Clicks, dismissals, dwell time → POST → Qdrant preference signals |
| Self-Learning (no model) | Python weight adjustments in `memory_extract_node` | Every turn. Programmatic, no LLM |
| Self-Learning (with model) | GPT-4o periodic reflection (async, ~20 turns) | Reviews patterns, suggests belief updates. Human-reviewable |
| Agent Orchestration | LangGraph | Attention + bias nodes slot into existing graph |
| Context Injection | Existing `chatbot_node` prompt assembly | Attention scores = multiplier on retrieval ranking |
| Transparency UI | React A2UI components (BeliefView, AttentionDebug) | Two-door: user sees what the agent sees |
| Embeddings | OpenAI text-embedding-3-small (1536d) | Already in stack via `memory.py` |
| Frontend | React + Tauri + AG-UI via CopilotKit | New components for belief/attention inspection |

Short version: Qdrant for storage, Python for scoring, LangGraph for orchestration, the LLM only when rule-based isn't enough.

## Full Technical Architecture

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                              TAURI DESKTOP SHELL                             │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │                         React Frontend (Vite)                           │ │
│  │                                                                         │ │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────────┐ ┌────────────┐  │ │
│  │  │Dashboard │ │Chat      │ │A2UI      │ │Belief     │ │Attention   │  │ │
│  │  │          │ │Panel     │ │Renderer  │ │View       │ │Debug       │  │ │
│  │  │ widgets, │ │          │ │          │ │           │ │            │  │ │
│  │  │ grid     │ │ messages │ │ renders  │ │ shows     │ │ shows why  │  │ │
│  │  │ layout   │ │ input    │ │ agent UI │ │ opinions  │ │ this was   │  │ │
│  │  │          │ │          │ │ surfaces │ │ + scores  │ │ surfaced   │  │ │
│  │  └────┬─────┘ └────┬─────┘ └────┬─────┘ └─────┬─────┘ └─────┬──────┘  │ │
│  │       │             │            │              │              │         │ │
│  │       └─────────────┴────────────┴──────────────┴──────────────┘         │ │
│  │                                  │                                       │ │
│  │                    ┌─────────────┴──────────────┐                        │ │
│  │                    │    Interaction Emitter      │                        │ │
│  │                    │                            │                        │ │
│  │                    │  click → POST /api/signal  │                        │ │
│  │                    │  dismiss → POST /api/signal│                        │ │
│  │                    │  dwell → POST /api/signal  │                        │ │
│  │                    │  ignore → inferred server  │                        │ │
│  │                    └─────────────┬──────────────┘                        │ │
│  │                                  │                                       │ │
│  └──────────────────────────────────┼───────────────────────────────────────┘ │
│                                     │                                        │
│              CopilotKit AG-UI       │  Vite proxy /api → :7101               │
│              useCoAgent state sync  │                                        │
└─────────────────────────────────────┼────────────────────────────────────────┘
                                      │
                                      ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                         FASTAPI BACKEND (:7101)                              │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │                          API Layer                                      │ │
│  │                                                                         │ │
│  │  /api/copilotkit    — AG-UI agent endpoint (SSE streaming)              │ │
│  │  /api/stocks/live   — SSE stock data stream                             │ │
│  │  /api/surface/close — canvas state sync                                 │ │
│  │  /api/signal        — interaction signals (NEW)                         │ │
│  │  /api/beliefs       — belief network inspection (NEW)                   │ │
│  │  /api/attention     — attention score debug (NEW)                       │ │
│  │                                                                         │ │
│  └──────────────────────────────┬──────────────────────────────────────────┘ │
│                                 │                                            │
│  ┌──────────────────────────────┴──────────────────────────────────────────┐ │
│  │                     LangGraph Agent (agent.py)                          │ │
│  │                                                                         │ │
│  │  ┌─────────┐    ┌─────────┐    ┌──────────────┐    ┌────────────────┐  │ │
│  │  │         │    │         │    │              │    │                │  │ │
│  │  │ chatbot │───▶│  tools  │───▶│   chatbot    │───▶│ memory_extract │  │ │
│  │  │  node   │    │  node   │    │   node       │    │    node        │  │ │
│  │  │         │    │         │    │  (if tools   │    │                │  │ │
│  │  │         │    │         │    │   called)    │    │ + attention    │  │ │
│  │  │         │    │         │    │              │    │   update       │  │ │
│  │  │         │    │         │    │              │    │ + bias check   │  │ │
│  │  └─────────┘    └─────────┘    └──────────────┘    └────────────────┘  │ │
│  │       │                                                    │           │ │
│  │       │              CONTEXT ASSEMBLY                      │           │ │
│  │       │              (before LLM call)                     │           │ │
│  │       │                                                    │           │ │
│  │       ▼                                                    ▼           │ │
│  │  ┌──────────────────────────────────────────────────────────────────┐  │ │
│  │  │                                                                  │  │ │
│  │  │  1. Domain Router    → classify intent                           │  │ │
│  │  │  2. Memory Manager   → top-5 memories (domain-filtered)          │  │ │
│  │  │  3. Graph Manager    → traverse entities + relationships         │  │ │
│  │  │  4. Attention Manager → score each result                        │  │ │
│  │  │     • temporal_score (how soon/recent)                           │  │ │
│  │  │     • interaction_score (engaged vs dismissed vs ignored)        │  │ │
│  │  │     • preference_weight (learned domain affinity)                │  │ │
│  │  │     • final = semantic_sim × temporal × interaction × preference │  │ │
│  │  │  5. Bias Detector    → check domain skew, apply corrections     │  │ │
│  │  │  6. Budget Enforcer  → 800 tokens max, rank by final score      │  │ │
│  │  │  7. Inject into system prompt                                    │  │ │
│  │  │                                                                  │  │ │
│  │  └──────────────────────────────────────────────────────────────────┘  │ │
│  │                                                                         │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │                      Supporting Modules                                 │ │
│  │                                                                         │ │
│  │  memory.py          — Qdrant vector store (memories + file_index)       │ │
│  │                       + belief network (opinion type + confidence)       │ │
│  │                                                                         │ │
│  │  domain_router.py   — keyword-based domain classification               │ │
│  │                       + cross-domain bridge rules                        │ │
│  │                                                                         │ │
│  │  graph_manager.py   — knowledge graph (entities + relationships)   (NEW)│ │
│  │                       + traversal + temporal scoring                     │ │
│  │                                                                         │ │
│  │  attention.py       — attention scoring + bias detection           (NEW)│ │
│  │                       + interaction signal processing                    │ │
│  │                                                                         │ │
│  │  reflection.py      — periodic LLM self-review (async)            (NEW)│ │
│  │                       + belief confidence updates                        │ │
│  │                       + adjustment recommendations                      │ │
│  │                                                                         │ │
│  │  workflow_engine.py  — pattern detection + learned automations           │ │
│  │  stock_streamer.py   — SSE live stock data broadcast                    │ │
│  │  tools_*.py          — domain tool modules (email, stock, travel, etc)  │ │
│  │  tracing.py          — Langfuse generation logging                      │ │
│  │                                                                         │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │                      Background Tasks                                   │ │
│  │                                                                         │ │
│  │  Email Poller        — checks email every 5 min                         │ │
│  │  Stock Streamer      — fetches yfinance every 60s, broadcasts SSE       │ │
│  │  Proactive Engine    — scans graph every 5 min for upcoming events (NEW)│ │
│  │  Reflection Loop     — LLM self-review every ~20 interactions     (NEW)│ │
│  │                                                                         │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
└──────────────────────────────┬───────────────────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                          QDRANT (:6333)                                       │
│                                                                              │
│  Collections:                                                                │
│                                                                              │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────────┐  │
│  │    memories      │  │   file_index    │  │      knowledge_graph        │  │
│  │                 │  │                 │  │                             │  │
│  │ types:          │  │ filename        │  │ entity_id                   │  │
│  │  fact           │  │ path            │  │ entity_type                 │  │
│  │  episode        │  │ domains         │  │ name                        │  │
│  │  reminder       │  │ summary         │  │ properties {}               │  │
│  │  workflow       │  │ file_type       │  │ relationships []            │  │
│  │  opinion (NEW)  │  │ indexed_at      │  │ domains []                  │  │
│  │                 │  │                 │  │ created_at                  │  │
│  │ + confidence    │  │                 │  │ updated_at                  │  │
│  │   (for opinion) │  │                 │  │ access_count                │  │
│  │ + preference    │  │                 │  │ attention_score (NEW)       │  │
│  │   signals       │  │                 │  │                             │  │
│  │                 │  │                 │  │ Relationships:              │  │
│  │ interaction     │  │                 │  │  target_id                  │  │
│  │ signals:        │  │                 │  │  relationship_type          │  │
│  │  engagement     │  │                 │  │  properties {}              │  │
│  │  dismissal      │  │                 │  │  created_at                 │  │
│  │  context_miss   │  │                 │  │                             │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────────────────┘  │
│                                                                              │
│  Vector: text-embedding-3-small (1536 dimensions)                            │
│  Distance: Cosine                                                            │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```


## Scale: Handling Thousands of Signals

The system is designed for a single user, but that user generates volume: thousands of emails, hundreds of calendar events, dozens of files, continuous stock feeds, and every interaction with the agent itself. The architecture handles this through tiered storage, progressive summarization, and attention budgets.

### Hot / Warm / Cold Storage Tiers

```
┌─────────────────────────────────────────────────────────────────┐
│                        STORAGE TIERS                            │
│                                                                 │
│  ┌─ HOT (in-memory, per-session) ──────────────────────────┐   │
│  │                                                          │   │
│  │  ~20 entities per heartbeat tick                         │   │
│  │  Current conversation context                            │   │
│  │  Active attention frame outputs                          │   │
│  │  Last 5 interaction signals                              │   │
│  │                                                          │   │
│  │  Storage: Python dicts in agent state                    │   │
│  │  Latency: <1ms                                           │   │
│  │  TTL: session lifetime                                   │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─ WARM (Qdrant, indexed + scored) ───────────────────────┐   │
│  │                                                          │   │
│  │  ~800 entities in knowledge graph                        │   │
│  │  Recent memories (last 30 days)                          │   │
│  │  Active beliefs with confidence > 0.3                    │   │
│  │  File index (all indexed files)                          │   │
│  │                                                          │   │
│  │  Storage: Qdrant collections (memories, knowledge_graph) │   │
│  │  Latency: 5-50ms (vector search)                         │   │
│  │  TTL: 30-day rolling window for memories,                │   │
│  │       permanent for entities                             │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─ COLD (summarized, archived) ───────────────────────────┐   │
│  │                                                          │   │
│  │  Older memories → compressed into summary memories       │   │
│  │  Past events → collapsed into entity properties          │   │
│  │  Dismissed beliefs → archived with final confidence      │   │
│  │  Historical interaction patterns → aggregated stats      │   │
│  │                                                          │   │
│  │  Storage: Qdrant (separate collection or tagged)         │   │
│  │  Latency: 50-200ms (rarely accessed)                     │   │
│  │  TTL: permanent, but only retrieved on explicit query    │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Progressive Summarization

Raw data doesn't stay raw forever. The system compresses over time:

```
Day 1:   "Email from Tom Bradley about Acme renewal pricing,
          $450K deal, needs response by Friday"
          → stored as full memory (warm tier)

Day 7:   Memory still accessed → stays warm, unchanged

Day 30:  Memory not accessed in 20 days →
          SUMMARIZE: "Acme renewal $450K — Tom Bradley contact,
          closed Q1" → replace original with summary
          → entity relationships preserved in knowledge graph

Day 90:  Summary not accessed →
          COLLAPSE into entity property:
          Acme Corp.properties.deals = ["$450K renewal Q1 2026"]
          → original memory archived to cold tier
```

This is not lossy compression — the knowledge graph retains the structural relationships (Tom → Acme → deal → file). Only the verbose narrative gets compressed. If the user asks "what happened with the Acme deal?", the graph traversal still connects all the dots, and the cold archive can be pulled if full detail is needed.

### Attention Budget

Every heartbeat tick has a budget. The system can't process 5000 emails per tick — it processes the 20 most relevant signals.

```
Per heartbeat tick (every 2 min):
  │
  ├─ Scan budget: 50 entities max across all frames
  │   (Qdrant filtered query, sorted by temporal + attention score)
  │
  ├─ Score budget: top 20 entities get full attention scoring
  │   (temporal × interaction × preference × bias correction)
  │
  ├─ Action budget: top 3 entities with score > 0.7 get surfaced
  │   (prevents notification overload)
  │
  └─ Context budget: 800 tokens max injected into agent prompt
      (400 memories + 400 graph context, deduplicated)
```

### Real-World Example: 5000 Emails

```
5000 emails in inbox
        │
        ▼
Entity Extraction (async, on ingest):
  → 800 unique entities extracted
    (people, companies, deals, events, topics)
  → stored in knowledge_graph collection
        │
        ▼
Heartbeat tick fires:
  → Finance frame scans: 12 entities with temporal relevance
  → Sales frame scans: 8 entities with upcoming deadlines
  → Personal frame scans: 3 entities with events today
  → Travel frame scans: 2 entities (upcoming trip)
        │
  Total scanned: 25 entities (from 800, not from 5000)
        │
        ▼
Attention scoring:
  → Top 20 scored
  → 3 surface to user (score > 0.7):
    1. "Acme meeting in 45 min — pricing doc attached"
    2. "NVDA down 4% — you have a position"
    3. "Helsinki flight tomorrow — hotel confirmation needed"
        │
        ▼
User sees 3 widgets. Not 5000 emails.
The system did the reading. The frames did the filtering.
The user gets the signal, not the noise.
```

The key insight: scale is handled by the knowledge graph, not by the LLM. The LLM never sees 5000 emails. It sees 3 pre-scored, pre-filtered, relationship-enriched context items. The graph is the compression layer. The attention frames are the filter. The LLM is the last mile.

## Memory as MCP Server

Memory shouldn't be locked inside one agent. It's infrastructure — like a database, not a feature. Any agent that connects should be able to remember, recall, and traverse the user's context.

The architecture exposes the entire memory + knowledge graph layer as an MCP (Model Context Protocol) server. Any MCP-compatible agent can plug in and get the same memory capabilities.

### Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                     MCP-COMPATIBLE AGENTS                        │
│                                                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────┐│
│  │ AstraOS  │  │ External │  │ CLI      │  │ Any MCP-         ││
│  │ Agent    │  │ Copilot  │  │ Agent    │  │ compatible agent  ││
│  │ (primary)│  │          │  │          │  │                   ││
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬──────────────┘│
│       │              │             │              │               │
│       └──────────────┴─────────────┴──────────────┘               │
│                              │                                    │
│                     MCP Protocol (stdio / SSE)                    │
│                              │                                    │
└──────────────────────────────┼────────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────┐
│                    MEMORY MCP SERVER                              │
│                                                                  │
│  Tools exposed via MCP:                                          │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │                                                            │  │
│  │  remember(content, type, tags, domains)                    │  │
│  │    → store a memory (fact, episode, reminder, opinion)     │  │
│  │    → auto-classifies domain if not provided                │  │
│  │    → returns memory_id                                     │  │
│  │                                                            │  │
│  │  recall(query, domains?, type?, limit?)                    │  │
│  │    → semantic search over memories                         │  │
│  │    → domain-filtered, attention-scored                     │  │
│  │    → returns ranked results with context                   │  │
│  │                                                            │  │
│  │  traverse(entity_name, depth?, relationship_types?)        │  │
│  │    → walk the knowledge graph from an entity               │  │
│  │    → returns connected entities + relationship paths       │  │
│  │    → cross-domain bridging when edges exist                │  │
│  │                                                            │  │
│  │  heartbeat_status()                                        │  │
│  │    → current attention frame states                        │  │
│  │    → top entities per frame with scores                    │  │
│  │    → last tick timestamp + next tick ETA                   │  │
│  │                                                            │  │
│  │  signal(entity_id, signal_type, metadata?)                 │  │
│  │    → report an interaction signal                          │  │
│  │    → signal_type: engagement, dismissal, ignore, miss      │  │
│  │    → feeds into self-learning loop                         │  │
│  │                                                            │  │
│  │  beliefs(domain?, min_confidence?)                         │  │
│  │    → list current beliefs/opinions                         │  │
│  │    → filtered by domain and confidence threshold           │  │
│  │    → includes evidence trail                               │  │
│  │                                                            │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                  │
│  Backed by:                                                      │
│    memory.py (MemoryManager)                                     │
│    graph_manager.py (GraphManager)                               │
│    attention.py (AttentionManager)                                │
│                                                                  │
│  Transport: stdio (local) or SSE (network)                       │
│  Config: standard mcp.json                                       │
│                                                                  │
└──────────────────────────────┬───────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────┐
│                          QDRANT (:6333)                           │
│                                                                  │
│  memories │ file_index │ knowledge_graph                         │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### Why MCP?

The memory layer is the most valuable part of the system. It's the user's digital twin — their relationships, preferences, beliefs, interaction history. Locking that inside a single agent is a waste.

With MCP:
- A coding agent (Kiro, Cursor) can `recall` what the user was working on and why
- A calendar agent can `traverse` from a meeting to the people involved to the relevant files
- A CLI tool can `remember` a decision the user made in the terminal
- A mobile agent can `recall` context from the desktop session
- Any new agent gets the full context layer on day one — no cold start

The memory is the platform. The agents are plugins.

### Example MCP Config

```json
{
  "mcpServers": {
    "astra-memory": {
      "command": "python",
      "args": ["-m", "memory_mcp_server"],
      "env": {
        "QDRANT_URL": "http://localhost:6333",
        "OPENAI_API_KEY": "${OPENAI_API_KEY}"
      },
      "autoApprove": ["recall", "traverse", "heartbeat_status", "beliefs"]
    }
  }
}
```

The `remember` and `signal` tools require approval by default — they write to the user's memory. Read operations are auto-approved. This follows the two-door principle: the agent can always read, but writing is gated.
