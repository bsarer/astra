import React, { useState, useCallback, useRef, useEffect } from "react";
import { useRenderToolCall } from "@copilotkit/react-core";
import { A2UIRenderer } from "./A2UIRenderer";

interface WindowState {
  surfaceId: string;
  components: any[];
  x: number;
  y: number;
  w: number;
  h: number;
  zIndex: number;
  minimized: boolean;
}

let nextZ = 10;

function clamp(val: number, min: number, max: number) {
  return Math.max(min, Math.min(max, val));
}

/** Compute a cascading position for new windows */
function cascadePosition(existing: WindowState[]): { x: number; y: number } {
  const base = 40;
  const step = 30;
  const count = existing.length;
  return { x: base + (count % 8) * step, y: base + (count % 8) * step };
}

/** Convert grid units (1-12 cols, row units) to pixel sizes */
function gridToPixels(grid?: { w?: number; h?: number }): { w: number; h: number } {
  const cols = grid?.w || 4;
  const rows = grid?.h || 3;
  return { w: clamp(cols * 80, 240, 900), h: clamp(rows * 80, 160, 700) };
}

/** Pretty-print surface ID as window title */
function surfaceTitle(id: string): string {
  return id.replace(/[-_]/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

export function Dashboard() {
  const [windows, setWindows] = useState<WindowState[]>([]);
  const dragRef = useRef<{ id: string; startX: number; startY: number; origX: number; origY: number } | null>(null);
  const resizeRef = useRef<{ id: string; startX: number; startY: number; origW: number; origH: number } | null>(null);
  const canvasRef = useRef<HTMLDivElement>(null);

  const handleAction = useCallback((action: string, payload?: Record<string, any>) => {
    console.log("[Dashboard] Action:", action, payload);
  }, []);

  const bringToFront = useCallback((id: string) => {
    nextZ += 1;
    setWindows((prev) => prev.map((w) => (w.surfaceId === id ? { ...w, zIndex: nextZ } : w)));
  }, []);

  const removeWindow = useCallback((id: string) => {
    setWindows((prev) => prev.filter((w) => w.surfaceId !== id));
  }, []);

  const toggleMinimize = useCallback((id: string) => {
    setWindows((prev) => prev.map((w) => (w.surfaceId === id ? { ...w, minimized: !w.minimized } : w)));
  }, []);

  const upsertWindow = useCallback((surfaceId: string, components: any[], grid?: { w?: number; h?: number }) => {
    setWindows((prev) => {
      const idx = prev.findIndex((w) => w.surfaceId === surfaceId);
      if (idx >= 0) {
        const next = [...prev];
        next[idx] = { ...next[idx], components };
        return next;
      }
      const pos = cascadePosition(prev);
      const size = gridToPixels(grid);
      nextZ += 1;
      return [...prev, { surfaceId, components, x: pos.x, y: pos.y, w: size.w, h: size.h, zIndex: nextZ, minimized: false }];
    });
  }, []);

  // Intercept emit_ui tool calls from the agent
  useRenderToolCall({
    name: "emit_ui",
    render: ({ status, args }) => {
      console.log("[Dashboard] emit_ui:", status, JSON.stringify(args));
      const { surface_id, components, grid } = args as {
        surface_id: string;
        components: any[];
        grid?: { w?: number; h?: number };
      };
      if (status === "complete" && surface_id && components?.length) {
        upsertWindow(surface_id, components, grid);
      }
      if (status !== "complete") {
        return (
          <div className="aios-widget-loading">
            <span className="aios-text--muted">Rendering {surface_id}…</span>
          </div>
        );
      }
      return <></>;
    },
  });

  // --- Mouse drag (title bar) ---
  const onTitleMouseDown = useCallback((e: React.MouseEvent, id: string) => {
    e.preventDefault();
    bringToFront(id);
    const win = windows.find((w) => w.surfaceId === id);
    if (!win) return;
    dragRef.current = { id, startX: e.clientX, startY: e.clientY, origX: win.x, origY: win.y };

    const onMove = (ev: MouseEvent) => {
      if (!dragRef.current) return;
      const dx = ev.clientX - dragRef.current.startX;
      const dy = ev.clientY - dragRef.current.startY;
      setWindows((prev) =>
        prev.map((w) =>
          w.surfaceId === dragRef.current!.id
            ? { ...w, x: Math.max(0, dragRef.current!.origX + dx), y: Math.max(0, dragRef.current!.origY + dy) }
            : w
        )
      );
    };
    const onUp = () => {
      dragRef.current = null;
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseup", onUp);
    };
    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
  }, [windows, bringToFront]);

  // --- Mouse resize (bottom-right handle) ---
  const onResizeMouseDown = useCallback((e: React.MouseEvent, id: string) => {
    e.preventDefault();
    e.stopPropagation();
    bringToFront(id);
    const win = windows.find((w) => w.surfaceId === id);
    if (!win) return;
    resizeRef.current = { id, startX: e.clientX, startY: e.clientY, origW: win.w, origH: win.h };

    const onMove = (ev: MouseEvent) => {
      if (!resizeRef.current) return;
      const dx = ev.clientX - resizeRef.current.startX;
      const dy = ev.clientY - resizeRef.current.startY;
      setWindows((prev) =>
        prev.map((w) =>
          w.surfaceId === resizeRef.current!.id
            ? { ...w, w: Math.max(200, resizeRef.current!.origW + dx), h: Math.max(100, resizeRef.current!.origH + dy) }
            : w
        )
      );
    };
    const onUp = () => {
      resizeRef.current = null;
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseup", onUp);
    };
    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
  }, [windows, bringToFront]);

  return (
    <div className="aios-dashboard aios-desktop" ref={canvasRef}>
      {/* Floating windows */}
      {windows.map((win) => (
        <div
          key={win.surfaceId}
          className={`aios-window${win.minimized ? " aios-window--minimized" : ""}`}
          style={{
            left: win.x,
            top: win.y,
            width: win.w,
            height: win.minimized ? "auto" : win.h,
            zIndex: win.zIndex,
          }}
          onMouseDown={() => bringToFront(win.surfaceId)}
        >
          {/* Title bar */}
          <div className="aios-window-titlebar" onMouseDown={(e) => onTitleMouseDown(e, win.surfaceId)}>
            <span className="aios-window-title">{surfaceTitle(win.surfaceId)}</span>
            <div className="aios-window-controls">
              <button
                className="aios-window-btn aios-window-btn--minimize"
                onClick={(e) => { e.stopPropagation(); toggleMinimize(win.surfaceId); }}
                aria-label="Minimize"
              >
                ─
              </button>
              <button
                className="aios-window-btn aios-window-btn--close"
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
          {/* Resize handle */}
          {!win.minimized && (
            <div className="aios-window-resize" onMouseDown={(e) => onResizeMouseDown(e, win.surfaceId)} />
          )}
        </div>
      ))}

      {/* Taskbar — minimized windows */}
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
