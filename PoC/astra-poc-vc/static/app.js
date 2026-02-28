// Initialize GridStack
let grid;

document.addEventListener('DOMContentLoaded', () => {
    // Initialize the grid layout
    grid = GridStack.init({
        cellHeight: 10, // 10px cells for fine-grained vertical resizing
        margin: 10,
        minRow: 1, // Don't collapse when empty
        float: true, // Allow widgets to be placed anywhere
        handle: '.drag-handle', // Only drag from the dedicated grip to prevent click/drag conflict on Shadow DOM
        resizable: {
            handles: 'se' // Only show bottom-right resizer. Invisible perimeter resizers were overlapping and hijacking button clicks!
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

    const chatForm = document.getElementById('chat-form');
    const messageInput = document.getElementById('message-input');

    chatForm.addEventListener('submit', async (e) => {
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
    // very basic markdown-to-br replacement for newlines in mock text
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

// Function to handle GenUI components
function renderGenUIComponent(componentData) {
    const { id, html, grid: gridOpts } = componentData;

    // Check if widget already exists
    if (activeWidgets[id]) {
        // Update existing widget content inside its shadow root
        const widgetBody = activeWidgets[id].querySelector('.widget-body');
        if (widgetBody && widgetBody.shadowRoot) {
            widgetBody.shadowRoot.innerHTML = html;
            // Execute scripts in the updated shadow DOM
            executeScriptsInElement(widgetBody.shadowRoot);
        }
        return;
    }

    // Default widget properties
    let widgetDef = {
        id: id,
        w: gridOpts?.w || 4, // Default to 4/12 (33%) width
        h: gridOpts?.h || 30, // Default to 300px height (1 cell = 10px)
        minW: 2, // Min 2 columns wide
        minH: 10, // Min 100px height
        // GridStack auto-wraps this in .grid-stack-item-content, so we only put children here
        content: `
            <span class="drag-handle" title="Drag to Move">⋮⋮</span>
            <span class="widget-close" onclick="removeWidget('${id}')">✕</span>
            <div class="widget-body" id="body-${id}"></div>
        `
    };

    // If specific positions are provided, use them
    if (gridOpts?.x !== undefined) widgetDef.x = gridOpts.x;
    if (gridOpts?.y !== undefined) widgetDef.y = gridOpts.y;

    // Add to grid
    const el = grid.addWidget(widgetDef);
    activeWidgets[id] = el;

    // Isolate rendering using an Iframe instead of Shadow DOM
    // This perfectly encapsulates globally-scoped JS like onclick="", which LLMs love to write
    const newlyAddedBody = el.querySelector(`#body-${id}`);
    if (newlyAddedBody) {
        const iframe = document.createElement('iframe');
        iframe.style.width = '100%';
        iframe.style.height = '100%';
        iframe.style.border = 'none';
        iframe.style.overflow = 'auto';
        iframe.style.display = 'block'; // Prevent inline gap errors
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
    }
}

// Function that widgets can call to send events back to the backend
// This effectively bridges the Widget UI logic back to the Agent
window.dispatchAgentEvent = function (eventName, payload) {
    console.log(`[Widget Event] ${eventName}:`, payload);
    appendMessage('system', `Widget Event triggered: ${eventName}`);
    sendMessage(JSON.stringify({ event: eventName, data: payload }), true);
};

async function sendMessage(text, isEvent = false) {
    if (!isEvent) {
        appendMessage('user', text);
    }
    setTyping(true);

    try {
        // We will hit the actual FastAPI endpoint
        const response = await fetch('/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ message: text })
        });

        if (!response.ok) {
            throw new Error(`Server error: ${response.status}`);
        }

        // Initialize empty string for streaming text collector
        let currentAssistantMessageDiv = null;

        // Handle SSE Text stream
        const reader = response.body.getReader();
        const decoder = new TextDecoder('utf-8');
        let buffer = '';

        while (true) {
            const { value, done } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });

            // Process Server Sent Events line by line
            let lines = buffer.split('\n');
            // keep the last line if it's incomplete
            buffer = lines.pop();

            for (const line of lines) {
                if (line.trim() === '') continue;
                if (line.startsWith('data: ')) {
                    const dataStr = line.substring(6).trim();
                    if (dataStr === '[DONE]') {
                        continue;
                    }

                    try {
                        const evt = JSON.parse(dataStr);

                        if (evt.type === 'message') {
                            if (!currentAssistantMessageDiv) {
                                currentAssistantMessageDiv = appendMessage('assistant', '');
                            }
                            // Append token
                            currentAssistantMessageDiv.innerHTML += evt.content.replace(/\n/g, '<br>');
                        } else if (evt.type === 'ui_component') {
                            // Render GenUI component!
                            renderGenUIComponent(evt.component);
                        }
                    } catch (e) {
                        console.error('Error parsing stream data:', e, dataStr);
                    }
                }
            }
        }
    } catch (error) {
        console.error('Chat error:', error);
        appendMessage('system', `Error: ${error.message}`);
    } finally {
        setTyping(false);
    }
}
