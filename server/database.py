"""Read-only SQLite access to the iMessage chat.db."""

import os
import sqlite3
from datetime import datetime, timezone

# Apple's epoch: 2001-01-01 00:00:00 UTC
APPLE_EPOCH_OFFSET = 978307200
NANOSECONDS = 1_000_000_000

DB_PATH = os.path.expanduser("~/Library/Messages/chat.db")


def _sanitize_text(text: str | None) -> str | None:
    """Remove surrogates and control chars that break JSON encoding."""
    if text is None:
        return None
    text = text.replace("\x00", "").replace("\x01", "")
    return text.encode("utf-8", errors="surrogatepass").decode("utf-8", errors="replace")


def get_connection() -> sqlite3.Connection:
    """Open a read-only connection to chat.db."""
    uri = f"file:{DB_PATH}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def apple_ts_to_unix(apple_ts: int | None) -> float | None:
    """Convert Apple Core Data timestamp (nanoseconds since 2001-01-01) to Unix timestamp."""
    if apple_ts is None or apple_ts == 0:
        return None
    return apple_ts / NANOSECONDS + APPLE_EPOCH_OFFSET


def unix_to_iso(unix_ts: float | None) -> str | None:
    """Convert Unix timestamp to ISO 8601 string in local time."""
    if unix_ts is None:
        return None
    return datetime.fromtimestamp(unix_ts).isoformat()


def get_conversations_on_day(month: int, day: int) -> list[dict]:
    """Return all conversations that have messages on the given month/day across all years."""
    mm_dd = f"{month:02d}-{day:02d}"

    conn = get_connection()
    try:
        # Find all chats that have at least one message on this calendar day
        rows = conn.execute(
            """
            SELECT
                c.ROWID as chat_id,
                c.display_name,
                c.style as chat_style,
                COUNT(DISTINCT m.ROWID) as message_count,
                GROUP_CONCAT(DISTINCT strftime('%Y',
                    datetime(m.date / 1000000000 + 978307200, 'unixepoch', 'localtime')
                )) as years,
                MAX(m.date) as last_date,
                c.chat_identifier
            FROM chat c
            JOIN chat_message_join cmj ON cmj.chat_id = c.ROWID
            JOIN message m ON m.ROWID = cmj.message_id
            WHERE strftime('%m-%d',
                datetime(m.date / 1000000000 + 978307200, 'unixepoch', 'localtime')
            ) = ?
            GROUP BY c.ROWID
            ORDER BY last_date DESC
            """,
            (mm_dd,),
        ).fetchall()

        conversations = []
        for row in rows:
            chat_id = row["chat_id"]
            years_str = row["years"] or ""
            years = sorted([int(y) for y in years_str.split(",") if y], reverse=True)

            # Get handles for this chat
            handles = conn.execute(
                """
                SELECT h.id
                FROM handle h
                JOIN chat_handle_join chj ON chj.handle_id = h.ROWID
                WHERE chj.chat_id = ?
                """,
                (chat_id,),
            ).fetchall()
            handle_list = [h["id"] for h in handles]

            # Get last message preview
            last_msg = conn.execute(
                """
                SELECT m.text, m.attributedBody
                FROM message m
                JOIN chat_message_join cmj ON cmj.message_id = m.ROWID
                WHERE cmj.chat_id = ?
                AND strftime('%m-%d',
                    datetime(m.date / 1000000000 + 978307200, 'unixepoch', 'localtime')
                ) = ?
                ORDER BY m.date DESC
                LIMIT 1
                """,
                (chat_id, mm_dd),
            ).fetchone()

            preview = None
            if last_msg:
                preview = last_msg["text"]
                if not preview and last_msg["attributedBody"]:
                    from server.message_parser import extract_text_from_attributed_body
                    preview = extract_text_from_attributed_body(last_msg["attributedBody"])

            is_group = (row["chat_style"] or 0) == 43
            display_name = row["display_name"] or row["chat_identifier"] or ""

            conversations.append({
                "chat_id": chat_id,
                "display_name": display_name,
                "handles": handle_list,
                "is_group": is_group,
                "message_count": row["message_count"],
                "years": years,
                "last_message_preview": (preview or "")[:100],
                "last_message_date": unix_to_iso(apple_ts_to_unix(row["last_date"])),
            })

        return conversations
    finally:
        conn.close()


def get_messages_for_chat_on_day(chat_id: int, month: int, day: int) -> dict:
    """Return all messages for a chat on the given month/day, grouped by year."""
    mm_dd = f"{month:02d}-{day:02d}"

    conn = get_connection()
    try:
        # Get chat info
        chat = conn.execute(
            "SELECT ROWID, display_name, style, chat_identifier FROM chat WHERE ROWID = ?",
            (chat_id,),
        ).fetchone()

        if not chat:
            return None

        is_group = (chat["style"] or 0) == 43

        # Get handles for this chat
        handle_rows = conn.execute(
            "SELECT h.id FROM handle h JOIN chat_handle_join chj ON chj.handle_id = h.ROWID WHERE chj.chat_id = ?",
            (chat_id,),
        ).fetchall()
        handles = [h["id"] for h in handle_rows]

        # Get messages on this day
        rows = conn.execute(
            """
            SELECT
                m.ROWID as message_id,
                m.text,
                m.attributedBody,
                m.is_from_me,
                m.date,
                m.date_read,
                m.handle_id,
                m.associated_message_guid,
                m.associated_message_type,
                h.id as handle_id_str,
                strftime('%Y',
                    datetime(m.date / 1000000000 + 978307200, 'unixepoch', 'localtime')
                ) as year
            FROM message m
            JOIN chat_message_join cmj ON cmj.message_id = m.ROWID
            LEFT JOIN handle h ON h.ROWID = m.handle_id
            WHERE cmj.chat_id = ?
            AND strftime('%m-%d',
                datetime(m.date / 1000000000 + 978307200, 'unixepoch', 'localtime')
            ) = ?
            ORDER BY m.date ASC
            """,
            (chat_id, mm_dd),
        ).fetchall()

        from server.message_parser import extract_text_from_attributed_body

        # Separate tapbacks from regular messages
        tapbacks_by_guid = {}
        regular_messages = []

        for row in rows:
            assoc_type = row["associated_message_type"] or 0
            if 2000 <= assoc_type <= 2005:
                # This is a tapback reaction
                guid = row["associated_message_guid"] or ""
                # Strip prefix like "p:0/" or "bp:"
                for prefix in ("p:0/", "p:1/", "bp:"):
                    if guid.startswith(prefix):
                        guid = guid[len(prefix):]
                        break
                tapbacks_by_guid.setdefault(guid, []).append({
                    "type": assoc_type,
                    "from_me": bool(row["is_from_me"]),
                })
            elif assoc_type >= 3000:
                # Tapback removal — ignore
                continue
            else:
                regular_messages.append(row)

        # Map tapback type to emoji
        TAPBACK_EMOJI = {
            2000: "\u2764\ufe0f",   # loved
            2001: "\ud83d\udc4d",   # liked
            2002: "\ud83d\udc4e",   # disliked
            2003: "\ud83d\ude02",   # laughed
            2004: "\u203c\ufe0f",   # emphasized
            2005: "\u2753",         # questioned
        }

        # Build year groups
        year_groups: dict[int, list] = {}
        for row in regular_messages:
            year = int(row["year"])

            text = _sanitize_text(row["text"])
            if not text and row["attributedBody"]:
                text = extract_text_from_attributed_body(row["attributedBody"])

            # Get attachments
            attachments = _get_attachments_for_message(conn, row["message_id"])

            # Get tapbacks for this message by GUID
            msg_guid_row = conn.execute(
                "SELECT guid FROM message WHERE ROWID = ?", (row["message_id"],)
            ).fetchone()
            msg_tapbacks = []
            if msg_guid_row:
                msg_guid = msg_guid_row["guid"]
                for tb in tapbacks_by_guid.get(msg_guid, []):
                    msg_tapbacks.append({
                        "type": tb["type"],
                        "emoji": TAPBACK_EMOJI.get(tb["type"], ""),
                        "from_me": tb["from_me"],
                    })

            msg = {
                "id": row["message_id"],
                "text": text,
                "is_from_me": bool(row["is_from_me"]),
                "date": unix_to_iso(apple_ts_to_unix(row["date"])),
                "date_read": unix_to_iso(apple_ts_to_unix(row["date_read"])),
                "year": year,
                "sender": None,
                "handle": row["handle_id_str"],
                "attachments": attachments,
                "tapbacks": msg_tapbacks,
            }

            year_groups.setdefault(year, []).append(msg)

        sorted_groups = [
            {"year": y, "messages": msgs}
            for y, msgs in sorted(year_groups.items())
        ]

        return {
            "chat_id": chat_id,
            "display_name": chat["display_name"] or chat["chat_identifier"] or "",
            "handles": handles,
            "is_group": is_group,
            "year_groups": sorted_groups,
        }
    finally:
        conn.close()


def _get_attachments_for_message(conn: sqlite3.Connection, message_id: int) -> list[dict]:
    """Get attachments for a specific message."""
    rows = conn.execute(
        """
        SELECT
            a.ROWID as attachment_id,
            a.filename,
            a.mime_type,
            a.transfer_name
        FROM attachment a
        JOIN message_attachment_join maj ON maj.attachment_id = a.ROWID
        WHERE maj.message_id = ?
        """,
        (message_id,),
    ).fetchall()

    attachments = []
    for row in rows:
        filename = row["transfer_name"] or row["filename"] or "attachment"
        attachments.append({
            "id": row["attachment_id"],
            "filename": filename,
            "mime_type": row["mime_type"],
            "url": f"/api/attachments/{row['attachment_id']}",
        })
    return attachments


def get_attachment_path(attachment_id: int) -> tuple[str | None, str | None]:
    """Return (file_path, mime_type) for an attachment."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT filename, mime_type FROM attachment WHERE ROWID = ?",
            (attachment_id,),
        ).fetchone()
        if not row or not row["filename"]:
            return None, None
        path = row["filename"].replace("~", os.path.expanduser("~"))
        # Decode URL-encoded characters in path (e.g. %20 → space)
        from urllib.parse import unquote
        path = unquote(path)
        return path, row["mime_type"]
    finally:
        conn.close()
