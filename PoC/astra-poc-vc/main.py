import os
import json
import re
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
from pydantic import BaseModel
from agent import get_agent_response_stream

# Load environment variables
load_dotenv()

app = FastAPI(title="LangChain GenUI Web Agent PoC")

# Mount static files (HTML, CSS, JS)
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=HTMLResponse)
async def read_root():
    """Serves the main frontend page."""
    with open("static/index.html", "r", encoding="utf-8") as f:
        return f.read()

class ChatRequest(BaseModel):
    message: str

@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    """
    Streams LangGraph events and captures GenUI components.
    """
    user_message = request.message
    
    async def event_generator():
        content_buffer = ""
        
        try:
            async for event in get_agent_response_stream(user_message, conversation_id="session_4"):
                kind = event["event"]
                name = event.get("name", "")
                
                # Check for streaming tokens from the LLM
                if kind == "on_chat_model_stream":
                    chunk = event["data"]["chunk"]
                    if hasattr(chunk, "content") and chunk.content:
                        content_buffer += chunk.content
                        yield f"data: {json.dumps({'type': 'message', 'content': chunk.content})}\n\n"
                        
                # Stream the UI widgets from tool calls!
                elif kind == "on_tool_start" and name == "render_widget":
                    tool_input = event["data"].get("input", {})
                    widget_data = {
                        "id": tool_input.get("id", "widget"),
                        "html": tool_input.get("html", ""),
                        "grid": {}
                    }
                    if "width_percent" in tool_input:
                        widget_data["grid"]["w"] = max(1, min(12, int(tool_input["width_percent"] * 12 / 100)))
                        
                    if "height_px" in tool_input:
                        widget_data["grid"]["h"] = max(1, int(int(tool_input["height_px"]) / 10))
                    yield f"data: {json.dumps({'type': 'ui_component', 'component': widget_data})}\n\n"
                
                # Fallback functionality for LLMs that don't emit on_chat_model_stream properly
                elif kind == "on_chain_end" and name == "chatbot":
                    node_output = event["data"].get("output", {})
                    if "messages" in node_output and node_output["messages"]:
                        last_message = node_output["messages"][-1]
                        
                        # Only yield text content if we haven't streamed anything
                        if hasattr(last_message, "content") and last_message.content and not content_buffer:
                            yield f"data: {json.dumps({'type': 'message', 'content': last_message.content})}\n\n"
                            
                        # And handle tools if on_tool_start somehow didn't fire
                        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
                            for tcall in last_message.tool_calls:
                                if tcall.get("name") == "render_widget":
                                    args = tcall.get("args", {})
                                    widget_data = {
                                        "id": args.get("id", "widget"),
                                        "html": args.get("html", ""),
                                        "grid": {}
                                    }
                                    if "width_percent" in args:
                                        widget_data["grid"]["w"] = max(1, min(12, int(args["width_percent"] * 12 / 100)))
                                        
                                    if "height_px" in args:
                                        widget_data["grid"]["h"] = max(1, int(int(args["height_px"]) / 10))
                                    yield f"data: {json.dumps({'type': 'ui_component', 'component': widget_data})}\n\n"
                        
        except Exception as e:
            print(f"Exception in graph stream: {e}")
            error_msg = f"\n\n[Error: {e}]"
            yield f"data: {json.dumps({'type': 'message', 'content': error_msg})}\n\n"

        # End stream
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    print(f"Starting server on http://localhost:{port}")
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
