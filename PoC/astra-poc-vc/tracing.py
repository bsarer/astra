"""Langfuse tracing helper — thin wrapper around the Langfuse SDK.

Set LANGFUSE_ENABLED=1 to log every LLM call: full context, token counts, latency.
"""

import os
import json
import logging
from typing import Optional

logger = logging.getLogger("astra.tracing")

_lf = None

if os.getenv("LANGFUSE_ENABLED", "0") == "1":
    try:
        from langfuse import Langfuse
        _lf = Langfuse(
            public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
            secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
            host=os.getenv("LANGFUSE_HOST", "http://host.docker.internal:3000"),
        )
        logger.info("Langfuse tracing enabled")
    except Exception as e:
        logger.warning("Langfuse init failed (non-critical): %s", e)


def _msg_to_dict(m) -> dict:
    """Normalize a LangChain message to an OpenAI-style dict."""
    role = getattr(m, "type", "user")
    role = {"human": "user", "ai": "assistant", "system": "system", "tool": "tool"}.get(role, role)
    content = m.content if isinstance(m.content, str) else json.dumps(m.content)
    return {"role": role, "content": content}


def log_generation(
    messages: list,
    response,
    model_name: str,
    tags: Optional[list[str]] = None,
) -> None:
    """Log a single LLM generation to Langfuse. No-op if tracing is disabled."""
    if not _lf:
        return
    try:
        usage = getattr(response, "usage_metadata", None) or getattr(response, "response_metadata", {})
        if isinstance(usage, dict):
            input_tokens = usage.get("input_tokens") or usage.get("prompt_tokens") or 0
            output_tokens = usage.get("output_tokens") or usage.get("completion_tokens") or 0
        else:
            input_tokens = getattr(usage, "input_tokens", 0)
            output_tokens = getattr(usage, "output_tokens", 0)

        resolved_model = getattr(response, "response_metadata", {}).get("model_name", model_name)
        output = response.content if isinstance(response.content, str) else json.dumps(response.content)

        trace = _lf.trace(name="astra_turn", tags=tags or ["astra"])
        trace.generation(
            name="chatbot",
            model=resolved_model,
            input=[_msg_to_dict(m) for m in messages],
            output=output,
            usage={"input": input_tokens, "output": output_tokens, "total": input_tokens + output_tokens},
        )
        _lf.flush()
    except Exception as e:
        logger.debug("Langfuse log failed (non-critical): %s", e)
