"""Resolve phone numbers and emails to contact names via macOS AddressBook."""

import glob
import os
import re
import sqlite3


_contact_cache: dict[str, str] = {}
_loaded = False


def _normalize_phone(phone: str) -> str:
    """Normalize a phone number to last 10 digits only."""
    digits = re.sub(r"\D", "", phone)
    if len(digits) > 10:
        digits = digits[-10:]
    return digits


def load_contacts():
    """Scan AddressBook SQLite databases and build the lookup cache."""
    global _contact_cache, _loaded

    if _loaded:
        return

    ab_pattern = os.path.expanduser(
        "~/Library/Application Support/AddressBook/Sources/*/AddressBook-v22.abcddb"
    )
    db_paths = glob.glob(ab_pattern)

    # Also check the main AddressBook database
    main_db = os.path.expanduser(
        "~/Library/Application Support/AddressBook/AddressBook-v22.abcddb"
    )
    if os.path.exists(main_db) and main_db not in db_paths:
        db_paths.append(main_db)

    for db_path in db_paths:
        try:
            uri = f"file:{db_path}?mode=ro"
            conn = sqlite3.connect(uri, uri=True)
            conn.row_factory = sqlite3.Row

            # Query phone numbers
            try:
                rows = conn.execute(
                    """
                    SELECT
                        r.ZFIRSTNAME,
                        r.ZLASTNAME,
                        p.ZFULLNUMBER
                    FROM ZABCDRECORD r
                    JOIN ZABCDPHONENUMBER p ON p.ZOWNER = r.Z_PK
                    WHERE p.ZFULLNUMBER IS NOT NULL
                    """
                ).fetchall()

                for row in rows:
                    first = row["ZFIRSTNAME"] or ""
                    last = row["ZLASTNAME"] or ""
                    name = f"{first} {last}".strip()
                    if name and row["ZFULLNUMBER"]:
                        normalized = _normalize_phone(row["ZFULLNUMBER"])
                        if normalized:
                            _contact_cache[normalized] = name
            except Exception:
                pass

            # Query email addresses
            try:
                rows = conn.execute(
                    """
                    SELECT
                        r.ZFIRSTNAME,
                        r.ZLASTNAME,
                        e.ZADDRESS
                    FROM ZABCDRECORD r
                    JOIN ZABCDEMAILADDRESS e ON e.ZOWNER = r.Z_PK
                    WHERE e.ZADDRESS IS NOT NULL
                    """
                ).fetchall()

                for row in rows:
                    first = row["ZFIRSTNAME"] or ""
                    last = row["ZLASTNAME"] or ""
                    name = f"{first} {last}".strip()
                    if name and row["ZADDRESS"]:
                        _contact_cache[row["ZADDRESS"].lower()] = name
            except Exception:
                pass

            conn.close()
        except Exception:
            continue

    _loaded = True


def resolve_name(handle: str) -> str:
    """Look up a contact name for a phone number or email. Returns handle if not found."""
    if not handle:
        return handle

    load_contacts()

    # Try direct email match
    if "@" in handle:
        name = _contact_cache.get(handle.lower())
        if name:
            return name
        return handle

    # Try phone match (last 10 digits)
    normalized = _normalize_phone(handle)
    if normalized:
        name = _contact_cache.get(normalized)
        if name:
            return name

    return handle


def _looks_like_identifier(name: str) -> bool:
    """Check if a display name looks like a raw phone number or chat identifier."""
    if not name:
        return True
    # Phone numbers start with + or are all digits
    stripped = name.strip()
    if stripped.startswith("+"):
        return True
    if stripped.replace("-", "").replace("(", "").replace(")", "").replace(" ", "").isdigit():
        return True
    # Chat identifiers like "chat503893739398632983"
    if stripped.startswith("chat") and stripped[4:].isdigit():
        return True
    return False


def resolve_conversation_name(display_name: str, handles: list[str], is_group: bool) -> str:
    """Resolve a display name for a conversation."""
    # If we have a real display name (not a phone/identifier), use it
    if display_name and not _looks_like_identifier(display_name):
        return display_name

    if not handles:
        # Try resolving the display_name itself as a handle
        if display_name:
            resolved = resolve_name(display_name)
            if resolved != display_name:
                return resolved
        return display_name or "Unknown"

    names = [resolve_name(h) for h in handles]
    if is_group:
        return ", ".join(names[:4]) + ("..." if len(names) > 4 else "")
    return names[0] if names else display_name or "Unknown"
