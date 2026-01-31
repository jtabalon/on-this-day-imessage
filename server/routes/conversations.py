"""GET /api/conversations — list conversations with messages on a given day."""

import json
import logging
from datetime import datetime

from fastapi import APIRouter, Query
from fastapi.responses import Response

from server.contacts import resolve_conversation_name, resolve_name
from server.database import get_conversations_on_day

logger = logging.getLogger(__name__)

router = APIRouter()


def _safe_json_response(data):
    """Return a JSON response that safely handles surrogate characters."""
    body = json.dumps(data, ensure_ascii=False, default=str)
    body_bytes = body.encode("utf-8", errors="replace")
    return Response(content=body_bytes, media_type="application/json")


@router.get("/conversations")
def list_conversations(
    month: int = Query(default=None, ge=1, le=12),
    day: int = Query(default=None, ge=1, le=31),
):
    now = datetime.now()
    if month is None:
        month = now.month
    if day is None:
        day = now.day

    conversations = get_conversations_on_day(month, day)

    # Resolve contact names and participant lists
    for conv in conversations:
        try:
            conv["display_name"] = resolve_conversation_name(
                conv["display_name"],
                conv["handles"],
                conv["is_group"],
            )
        except Exception:
            logger.debug("Failed to resolve conversation name for chat %s", conv.get("chat_id"), exc_info=True)
        participants = []
        for h in conv["handles"]:
            try:
                participants.append(resolve_name(h))
            except Exception:
                logger.debug("Failed to resolve contact name for handle %r", h, exc_info=True)
                participants.append(h)
        conv["participants"] = participants

    return _safe_json_response({"month": month, "day": day, "conversations": conversations})
