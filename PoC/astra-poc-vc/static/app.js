// ─── Debug Panel ───

const DebugPanel = {
    _enabled: false,
    _panel: null,
    _log: null,
    _badge: null,
    _msgCount: 0,
    _buffer: [],

    init() {
        this._panel = document.getElementById('debug-panel');
        this._log = document.getElementById('debug-log');
        this._badge = document.getElementById('debug-badge');

        // Flush any messages that arrived before init
        if (this._log && this._buffer.length) {
            this._buffer.forEach(b => this._appendEntry(b.direction, b.data));
            this._buffer = [];
        }
    },

    toggle() {
        this._enabled = !this._enabled;
        if (this._panel) {
            this._panel.classList.toggle('open', this._enabled);
        }
        const btn = document.getElementById('debug-toggle');
        if (btn) {
            btn.classList.toggle('active', this._enabled);
            btn.title = this._enabled ? 'Hide Debug Panel' : 'Show Debug Panel';
        }
    },

    log(direction, data) {
        if (!this._log) {
            // Buffer until init runs
            this._buffer.push({ direction, data });
            return;
        }
        this._appendEntry(direction, data);
    },

    _appendEntry(direction, data) {
        this._msgCount++;
        const time = new Date().toLocaleTimeString('en-US', {
            hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit', fractionalSecondDigits: 3
        });
        const arrow = direction === 'send' ? '⬆' : '⬇';
        const cls = direction === 'send' ? 'debug-send' : 'debug-recv';
        const raw = typeof data === 'string' ? data : JSON.stringify(data);
        const preview = raw.length > 300 ? raw.slice(0, 300) + '…' : raw;

        const entry = document.createElement('div');
        entry.className = `debug-entry ${cls}`;
        entry.innerHTML =
            `<span class="debug-time">${time}</span> ` +
            `<span class="debug-arrow">${arrow}</span> ` +
            `<span class="debug-body">${this._esc(preview)}</span>`;
        entry.title = raw;
        this._log.appendChild(entry);
        this._log.scrollTop = this._log.scrollHeight;

        if (this._badge) {
            this._badge.textContent = this._msgCount;
            this._badge.style.display = 'inline-block';
        }
    },

    clear() {
        if (this._log) this._log.innerHTML = '';
        this._msgCount = 0;
        if (this._badge) this._badge.style.display = 'none';
    },

    _esc(str) {
        const d = document.createElement('div');
        d.textContent = str;
        return d.innerHTML;
    }
};

// ─── AgentConnection: WebSocket client with reconnect ───

class AgentConnection {
    constructor() {
        this._sessionId = null;
        this._ws = null;
        this._retryCount = 0;
        this._maxRetries = 5;
        this._retryDelays = [1000, 2000, 4000, 8000, 16000];
        this._callbacks = {
            token: null,
            widget: null,
            done: null,
            error: null,
            session_init: null,
        };
        this._connect();
    }

    _buildUrl() {
        const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        let url = `${proto}//${window.location.host}/ws`;
        if (this._sessionId) {
            url += `?session_id=${encodeURIComponent(this._sessionId)}`;
        }
        return url;
    }

    _connect() {
        const url = this._buildUrl();
        this._ws = new WebSocket(url);

        this._ws.onopen = () => {
            console.log('[AgentConnection] connected');
            this._retryCount = 0;
        };

        this._ws.onmessage = (event) => {
            try {
                const msg = JSON.parse(event.data);
                DebugPanel.log('recv', msg);
                if (msg.type === 'session_init' && msg.session_id) {
                    this._sessionId = msg.session_id;
                }
                const cb = this._callbacks[msg.type];
                if (cb) cb(msg);
            } catch (e) {
                console.error('[AgentConnection] failed to parse message:', e);
            }
        };

        this._ws.onclose = () => {
            console.log('[AgentConnection] disconnected');
            this.reconnect();
        };
    }

    send(message) {
        if (this._ws && this._ws.readyState === WebSocket.OPEN) {
            DebugPanel.log('send', message);
            this._ws.send(JSON.stringify(message));
        } else {
            console.warn('[AgentConnection] cannot send, socket not open');
        }
    }

    onToken(callback) { this._callbacks.token = callback; }
    onWidget(callback) { this._callbacks.widget = callback; }
    onDone(callback) { this._callbacks.done = callback; }
    onError(callback) { this._callbacks.error = callback; }
    onSessionInit(callback) { this._callbacks.session_init = callback; }

    reconnect() {
        if (this._retryCount >= this._maxRetries) {
            console.error('[AgentConnection] max retries reached, giving up');
            return;
        }
        const delay = this._retryDelays[this._retryCount] || this._retryDelays[this._retryDelays.length - 1];
        this._retryCount++;
        console.log(`[AgentConnection] reconnecting in ${delay}ms (attempt ${this._retryCount}/${this._maxRetries})`);
        setTimeout(() => this._connect(), delay);
    }

    close() {
        if (this._ws) {
            this._ws.onclose = null; // prevent reconnect on intentional close
            this._ws.close();
            this._ws = null;
        }
    }
}

// ─── GridStack + UI helpers (unchanged) ───

let grid;
let agentConnection;
let currentAssistantMessageDiv = null;

document.addEventListener('DOMContentLoaded', () => {
    // Initialize debug panel
    DebugPanel.init();

    // Initialize the grid layout
    grid = GridStack.init({
        cellHeight: 10,
        margin: 10,
        minRow: 1,
        float: true,
        handle: '.drag-handle',
        resizable: {
            handles: 'se'
        }
    });

    // Handle iframe event trapping during resize and drag
    grid.on('dragstart resizestart', function (event, el) {
        const iframes = el.querySelectorAll('iframe');
        iframes.forEach(iframe => iframe.style.pointerEvents = 'none');
    });

    grid.on('dragstop resizestop', function (event, el) {
        const iframes = el.querySelectorAll('iframe');
        iframes.forEach(iframe => iframe.style.pointerEvents = 'auto');
    });

    // Initialize WebSocket connection
    agentConnection = new AgentConnection();

    agentConnection.onToken((msg) => {
        if (!currentAssistantMessageDiv) {
            currentAssistantMessageDiv = appendMessage('assistant', '');
        }
        currentAssistantMessageDiv.innerHTML += msg.content.replace(/\n/g, '<br>');
        chatMessages.scrollTop = chatMessages.scrollHeight;
    });

    agentConnection.onWidget((msg) => {
        renderGenUIComponent(msg);
    });

    agentConnection.onDone(() => {
        currentAssistantMessageDiv = null;
        setTyping(false);
    });

    agentConnection.onError((msg) => {
        appendMessage('system', `Error: ${msg.content}`);
        setTyping(false);
    });

    agentConnection.onSessionInit((msg) => {
        console.log('[Session] initialized with id:', msg.session_id);
    });

    const chatForm = document.getElementById('chat-form');
    const messageInput = document.getElementById('message-input');

    chatForm.addEventListener('submit', (e) => {
        e.preventDefault();
        const message = messageInput.value.trim();
        if (!message) return;

        sendMessage(message);
        messageInput.value = '';
    });
});

// UI helpers
const chatMessages = document.getElementById('chat-messages');
const typingIndicator = document.getElementById('typing-indicator');
const sendBtn = document.getElementById('send-btn');
const messageInput = document.getElementById('message-input');

function appendMessage(role, content) {
    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${role}`;
    msgDiv.innerHTML = content.replace(/\n/g, '<br>');
    chatMessages.appendChild(msgDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    return msgDiv;
}

function setTyping(isTyping) {
    typingIndicator.style.display = isTyping ? 'block' : 'none';
    sendBtn.disabled = isTyping;
    messageInput.disabled = isTyping;
    if (isTyping) {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
}

// Global registry to store references to active widgets
const activeWidgets = {};
// Track pinned state per widget
const pinnedWidgets = {};

// Function to handle GenUI components
function renderGenUIComponent(componentData) {
    const { id, html, grid: gridOpts } = componentData;

    // Check if widget already exists
    if (activeWidgets[id]) {
        // Update existing widget content inside its shadow root
        const widgetBody = activeWidgets[id].querySelector('.widget-body');
        if (widgetBody && widgetBody.shadowRoot) {
            widgetBody.shadowRoot.innerHTML = html;
            executeScriptsInElement(widgetBody.shadowRoot);
        }
        return;
    }

    // Default widget properties
    let widgetDef = {
        id: id,
        w: gridOpts?.w || 4,
        h: gridOpts?.h || 30,
        minW: 2,
        minH: 10,
        content: `
            <span class="drag-handle" title="Drag to Move">⋮⋮</span>
            <span class="widget-pin" onclick="togglePin('${id}')" title="Pin widget">📌</span>
            <span class="widget-close" onclick="removeWidget('${id}')">✕</span>
            <div class="widget-body" id="body-${id}"></div>
        `
    };

    if (gridOpts?.x !== undefined) widgetDef.x = gridOpts.x;
    if (gridOpts?.y !== undefined) widgetDef.y = gridOpts.y;

    // Add to grid
    const el = grid.addWidget(widgetDef);
    activeWidgets[id] = el;

    // Isolate rendering using an Iframe
    const newlyAddedBody = el.querySelector(`#body-${id}`);
    if (newlyAddedBody) {
        const iframe = document.createElement('iframe');
        iframe.style.width = '100%';
        iframe.style.height = '100%';
        iframe.style.border = 'none';
        iframe.style.overflow = 'auto';
        iframe.style.display = 'block';
        iframe.style.borderRadius = '16px';

        const baseStyle = `
            <style>
                html { height: 100%; width: 100%; margin: 0; padding: 0; }
                body { 
                    margin: 0; padding: 0; 
                    height: 100%; width: 100%; 
                    font-family: 'Inter', system-ui, sans-serif;
                    color: #f8fafc;
                    box-sizing: border-box;
                    overflow: hidden;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                }
                ::-webkit-scrollbar { display: none; }
                * { box-sizing: border-box; }
            </style>
        `;

        const bridgeScript = `
            <script>
                window.dispatchAgentEvent = function(eventName, payload) {
                    if (window.parent && window.parent.dispatchAgentEvent) {
                        window.parent.dispatchAgentEvent(eventName, payload);
                    }
                };
            </script>
        `;

        iframe.srcdoc = `<!DOCTYPE html><html><head>${baseStyle}${bridgeScript}</head><body>${html}</body></html>`;
        newlyAddedBody.appendChild(iframe);
    }
}

function removeWidget(id) {
    if (activeWidgets[id]) {
        grid.removeWidget(activeWidgets[id]);
        delete activeWidgets[id];
        delete pinnedWidgets[id];
    }
}

function togglePin(id) {
    const el = activeWidgets[id];
    if (!el) return;
    const isPinned = !pinnedWidgets[id];
    pinnedWidgets[id] = isPinned;

    // Lock/unlock the widget in GridStack
    grid.update(el, { noMove: isPinned, noResize: isPinned });

    // Visual feedback
    const pinBtn = el.querySelector('.widget-pin');
    if (pinBtn) {
        pinBtn.classList.toggle('pinned', isPinned);
        pinBtn.title = isPinned ? 'Unpin widget' : 'Pin widget';
    }
    el.querySelector('.grid-stack-item-content')?.classList.toggle('widget-pinned', isPinned);
}

// ─── Communication layer (WebSocket-based) ───

// Widget event bridge: sends widget_event over WebSocket
window.dispatchAgentEvent = function (eventName, payload) {
    console.log(`[Widget Event] ${eventName}:`, payload);
    if (agentConnection) {
        agentConnection.send({
            type: 'widget_event',
            event_name: eventName,
            payload: payload
        });
    }
};

function sendMessage(text) {
    appendMessage('user', text);
    setTyping(true);
    if (agentConnection) {
        agentConnection.send({ type: 'user_message', content: text });
    }
}
