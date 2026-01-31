"""Message and attachment routes."""

import json
import os
import subprocess
import tempfile
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse, Response

from server.contacts import resolve_conversation_name, resolve_name
from server.database import get_attachment_path, get_messages_for_chat_on_day


def _safe_json_response(data):
    """Return a JSON response that safely handles surrogate characters."""
    body = json.dumps(data, ensure_ascii=False, default=str)
    # Encode replacing surrogates
    body_bytes = body.encode("utf-8", errors="replace")
    return Response(content=body_bytes, media_type="application/json")

router = APIRouter()

CACHE_DIR = os.path.join(tempfile.gettempdir(), "on-this-day-imessage-cache")
os.makedirs(CACHE_DIR, exist_ok=True)


@router.get("/conversations/{chat_id}/messages")
def get_messages(
    chat_id: int,
    month: int = Query(default=None, ge=1, le=12),
    day: int = Query(default=None, ge=1, le=31),
):
    now = datetime.now()
    if month is None:
        month = now.month
    if day is None:
        day = now.day

    result = get_messages_for_chat_on_day(chat_id, month, day)
    if result is None:
        raise HTTPException(status_code=404, detail="Chat not found")

    # Resolve contact names
    result["display_name"] = resolve_conversation_name(
        result["display_name"],
        result.get("handles", []),
        result["is_group"],
    )

    for group in result["year_groups"]:
        for msg in group["messages"]:
            if msg["handle"]:
                msg["sender"] = resolve_name(msg["handle"])
            elif msg["is_from_me"]:
                msg["sender"] = "Me"

    return _safe_json_response(result)


@router.get("/attachments/{attachment_id}")
def serve_attachment(attachment_id: int):
    path, mime_type = get_attachment_path(attachment_id)
    if not path or not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Attachment not found")

    # HEIC → JPEG conversion
    if (mime_type and "heic" in mime_type.lower()) or path.lower().endswith(".heic"):
        converted = _convert_heic(path, attachment_id)
        if converted and os.path.exists(converted):
            return FileResponse(converted, media_type="image/jpeg")

    return FileResponse(path, media_type=mime_type or "application/octet-stream")


def _convert_heic(source: str, attachment_id: int) -> str | None:
    """Convert HEIC to JPEG using sips, caching the result."""
    out_path = os.path.join(CACHE_DIR, f"{attachment_id}.jpg")
    if os.path.exists(out_path):
        return out_path
    try:
        subprocess.run(
            ["sips", "-s", "format", "jpeg", source, "--out", out_path],
            check=True,
            capture_output=True,
            timeout=10,
        )
        return out_path
    except Exception:
        return None
