import { useState, useCallback, useRef, useEffect } from "react";
import { useCoAgent, useCopilotChat } from "@copilotkit/react-core";
import GridLayout, { Layout } from "react-grid-layout";
import { A2UIRenderer } from "./A2UIRenderer";
import "react-grid-layout/css/styles.css";
import "react-resizable/css/styles.css";

interface AgentState {
  ui_event: {
    surface_id: string;
    components: any[];
    grid?: { w?: number; h?: number };
  } | null;
  needs_ui: boolean;
}

interface WindowData {
  surfaceId: string;
  components: any[];
  minimized: boolean;
}

// Map widget button actions to chat messages
const ACTION_MESSAGES: Record<string, string> = {
  show_inbox: "show me my inbox",
  show_calendar: "show me my calendar",
  show_stocks: "show me my stocks",
  show_files: "show me my files",
  read_file: "read file",
};

/** Pretty-print surface ID as window title */
function surfaceTitle(id: string): string {
  return id.replace(/[-_]/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

// Grid constants
const GRID_COLS = 12;
const ROW_HEIGHT = 60;

export function Dashboard() {
  const [windowData, setWindowData] = useState<Map<string, WindowData>>(new Map());
  const [layout, setLayout] = useState<Layout[]>([]);
  const containerRef = useRef<HTMLDivElement>(null);
  const [containerWidth, setContainerWidth] = useState(1200);
  // Track manually closed windows so agent state can't re-open them
  const closedWindows = useRef<Set<string>>(new Set());

  const { appendMessage } = useCopilotChat();

  // Measure container width for GridLayout
  useEffect(() => {
    const measure = () => {
      if (containerRef.current) {
        setContainerWidth(containerRef.current.offsetWidth);
      }
    };
    measure();
    window.addEventListener("resize", measure);
    return () => window.removeEventListener("resize", measure);
  }, []);

  const handleAction = useCallback((action: string, payload?: Record<string, any>) => {
    console.log("[Dashboard] Action:", action, payload);
    let msg = ACTION_MESSAGES[action];
    if (!msg) return;
    if (action === "read_file" && payload?.filename) {
      msg = `read file ${payload.filename}`;
    }
    appendMessage({ id: crypto.randomUUID(), role: "user", content: msg } as any);
  }, [appendMessage]);

  const removeWindow = useCallback((id: string) => {
    closedWindows.current.add(id);
    setWindowData((prev) => {
      const next = new Map(prev);
      next.delete(id);
      return next;
    });
    setLayout((prev) => prev.filter((l) => l.i !== id));
  }, []);

  const toggleMinimize = useCallback((id: string) => {
    setWindowData((prev) => {
      const next = new Map(prev);
      const win = next.get(id);
      if (win) {
        next.set(id, { ...win, minimized: !win.minimized });
      }
      return next;
    });
  }, []);

  const upsertWindow = useCallback((surfaceId: string, components: any[], grid?: { w?: number; h?: number }) => {
    // Don't re-open windows the user explicitly closed
    if (closedWindows.current.has(surfaceId)) return;
    setWindowData((prev) => {
      const next = new Map(prev);
      const existing = next.get(surfaceId);
      next.set(surfaceId, {
        surfaceId,
        components,
        minimized: existing?.minimized ?? false,
      });
      return next;
    });

    setLayout((prev) => {
      const exists = prev.find((l) => l.i === surfaceId);
      if (exists) {
        // Update existing - keep position, optionally update size
        return prev;
      }
      // New window - let GridLayout auto-place by omitting x,y
      // GridLayout will find the first empty spot
      const w = grid?.w || 4;
      const h = grid?.h || 3;
      return [...prev, { i: surfaceId, w, h, x: 0, y: Infinity }];
      // y: Infinity means "place at the bottom" but compactType will move it up
    });
  }, []);

  const { state: agentState } = useCoAgent<AgentState>({
    name: "astra_agent",
    initialState: { ui_event: null, needs_ui: false },
  });

  // Watch ui_event from agent state
  const lastSurfaceRef = useRef<string | null>(null);
  useEffect(() => {
    const ev = agentState?.ui_event;
    if (!ev?.surface_id || !ev?.components?.length) return;
    const key = `${ev.surface_id}:${ev.components.length}`;
    if (lastSurfaceRef.current === key) return;
    lastSurfaceRef.current = key;
    console.log("[Dashboard] useCoAgent ui_event:", ev.surface_id, ev.components.length);
    upsertWindow(ev.surface_id, ev.components, ev.grid ?? undefined);
  }, [agentState?.ui_event, upsertWindow]);

  const onLayoutChange = useCallback((newLayout: Layout[]) => {
    setLayout(newLayout);
  }, []);

  const windows = Array.from(windowData.values());

  return (
    <div className="aios-dashboard aios-desktop" ref={containerRef}>
      <GridLayout
        className="aios-grid-layout"
        layout={layout}
        cols={GRID_COLS}
        rowHeight={ROW_HEIGHT}
        width={containerWidth}
        onLayoutChange={onLayoutChange}
        draggableHandle=".aios-window-titlebar"
        compactType="vertical"
        preventCollision={false}
        isResizable={true}
        isDraggable={true}
        margin={[12, 12]}
        containerPadding={[16, 16]}
      >
        {windows.map((win) => (
          <div
            key={win.surfaceId}
            className={`aios-window${win.minimized ? " aios-window--minimized" : ""}`}
          >
            {/* Title bar */}
            <div className="aios-window-titlebar">
              <span className="aios-window-title">{surfaceTitle(win.surfaceId)}</span>
              <div className="aios-window-controls">
                <button
                  className="aios-window-btn aios-window-btn--minimize"
                  onMouseDown={(e) => e.stopPropagation()}
                  onClick={(e) => { e.stopPropagation(); toggleMinimize(win.surfaceId); }}
                  aria-label="Minimize"
                >
                  ─
                </button>
                <button
                  className="aios-window-btn aios-window-btn--close"
                  onMouseDown={(e) => e.stopPropagation()}
                  onClick={(e) => { e.stopPropagation(); removeWindow(win.surfaceId); }}
                  aria-label="Close"
                >
                  ✕
                </button>
              </div>
            </div>
            {/* Content */}
            {!win.minimized && (
              <div className="aios-window-body">
                <A2UIRenderer components={win.components} onAction={handleAction} />
              </div>
            )}
          </div>
        ))}
      </GridLayout>

      {/* Taskbar for minimized windows */}
      {windows.some((w) => w.minimized) && (
        <div className="aios-taskbar">
          {windows.filter((w) => w.minimized).map((w) => (
            <button
              key={w.surfaceId}
              className="aios-taskbar-item"
              onClick={() => toggleMinimize(w.surfaceId)}
            >
              {surfaceTitle(w.surfaceId)}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
