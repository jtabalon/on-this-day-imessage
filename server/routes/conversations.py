"""GET /api/conversations — list conversations with messages on a given day."""

import json
from datetime import datetime

from fastapi import APIRouter, Query
from fastapi.responses import Response

from server.contacts import resolve_conversation_name, resolve_name
from server.database import get_conversations_on_day

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

    # Resolve contact names
    for conv in conversations:
        conv["display_name"] = resolve_conversation_name(
            conv["display_name"],
            conv["handles"],
            conv["is_group"],
        )

    return _safe_json_response({"month": month, "day": day, "conversations": conversations})
