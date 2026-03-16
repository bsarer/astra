"""Background email poller — checks for new emails and triggers agent notifications.

Extracted from main.py for clarity. Called as an asyncio background task.
"""

import asyncio
import logging

logger = logging.getLogger("astra.poller")


async def run_email_poller(
    active_connections: dict,
    seen_email_ids: set,
    get_session_lock,
    handle_user_message,
    poll_interval: int = 300,
):
    """Background task: polls for new emails and triggers agent for relevant ones.

    Args:
        active_connections: dict of session_id -> WebSocket
        seen_email_ids: set of already-processed email IDs (mutated in place)
        get_session_lock: callable(session_id) -> asyncio.Lock
        handle_user_message: async callable(ws, prompt, session_id)
        poll_interval: seconds between polls
    """
    from providers.factory import get_email_provider

    logger.info("Email poller started (interval=%ds)", poll_interval)

    # Wait for first connection
    while not active_connections:
        await asyncio.sleep(2)

    await asyncio.sleep(10)  # let background fetch seed seen IDs first

    # Seed seen IDs from current inbox
    try:
        provider = get_email_provider()
        initial = await provider.list_emails(limit=20)
        for e in initial:
            seen_email_ids.add(e.id)
        logger.info("Email poller seeded with %d existing email IDs", len(seen_email_ids))
    except Exception as ex:
        logger.warning("Email poller seed failed: %s", ex)

    while True:
        await asyncio.sleep(poll_interval)
        if not active_connections:
            continue

        try:
            provider = get_email_provider()
            emails = await provider.list_emails(limit=10)
            new_emails = [e for e in emails if e.id not in seen_email_ids]
            if not new_emails:
                continue

            for e in new_emails:
                seen_email_ids.add(e.id)

            logger.info("Email poller found %d new email(s)", len(new_emails))

            for e in new_emails:
                prompt = _build_email_prompt(e)
                for sid, ws in list(active_connections.items()):
                    lock = get_session_lock(sid)
                    try:
                        async with lock:
                            await handle_user_message(ws, prompt, sid)
                    except Exception as ex:
                        logger.warning("Poller push failed for session %s: %s", sid, ex)

        except Exception as ex:
            logger.warning("Email poller error: %s", ex)


def _build_email_prompt(email) -> str:
    """Build the agent prompt for a new email notification."""
    return (
        f"[SYSTEM] New email detected by background poller:\n\n"
        f"From: {email.from_addr}\n"
        f"Subject: {email.subject}\n"
        f"Body: {email.body[:500]}\n\n"
        f"INSTRUCTIONS: Check if this email mentions any stocks from Mike's "
        f"watchlist (AAPL, MSFT, NVDA, TSLA, GOOG, AMZN, META). "
        f"If it does, call `analyze_stock_email_context` with the subject, body, and email_id='{email.id}', "
        f"then call `get_stock_quote` for each matched ticker, "
        f"then render a stock alert widget with id 'stock-alert'. "
        f"If the email is NOT stock-related, just show a brief notification "
        f"like 'New email from [sender]: [subject]'."
    )
