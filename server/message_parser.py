"""Extract text from iMessage attributedBody (NSKeyedArchive typedstream) blobs."""


def extract_text_from_attributed_body(blob: bytes) -> str | None:
    """Parse the attributedBody blob to extract the plain-text string.

    The blob is an NSKeyedArchive / typedstream. The text is stored as a
    length-prefixed UTF-8 string following an NSString marker. We use a
    heuristic search rather than a full archive decoder.

    Observed encoding after "NSString":
        \x01 <type_byte> \x84 \x01 + <length> <utf8_text>
    where <length> can be:
        - 1 byte (0x01-0x7f) for strings up to 127 bytes
        - \x81 <1 byte> for strings 128-255 bytes
        - \x84 <4 bytes big-endian> for longer strings
    """
    if not blob:
        return None

    try:
        # Strategy 1: Find NSString marker, then locate the \x01+ pattern
        # and read the length-prefixed text after it.
        marker = b"NSString"
        idx = blob.find(marker)
        if idx == -1:
            marker = b"NSMutableString"
            idx = blob.find(marker)
        if idx != -1:
            text = _parse_after_nsstring(blob, idx + len(marker))
            if text:
                return _clean(text)

        # Strategy 2: scan for the longest UTF-8 run in the blob
        text = _scan_for_utf8_run(blob)
        if text:
            return _clean(text)

    except Exception:
        pass

    return None


def _parse_after_nsstring(blob: bytes, start: int) -> str | None:
    """Parse the text content after an NSString marker.

    Look for the \x01+ (0x01 0x2b) byte pattern which precedes the
    length-prefixed text in the typedstream encoding.
    """
    # Search for \x01+ pattern within 20 bytes of the marker
    search_end = min(start + 20, len(blob) - 2)
    for pos in range(start, search_end):
        if blob[pos] == 0x01 and blob[pos + 1] == 0x2b:  # \x01+
            # The length-prefixed text starts right after \x01+
            return _read_length_prefixed(blob, pos + 2)
    return None


def _read_length_prefixed(blob: bytes, pos: int) -> str | None:
    """Read a length-prefixed UTF-8 string at the given position."""
    if pos >= len(blob):
        return None

    byte = blob[pos]

    # Single-byte length (1-127)
    if 1 <= byte <= 0x7F:
        length = byte
        str_start = pos + 1
    # Two-byte length: 0x81 followed by 1 byte
    elif byte == 0x81 and pos + 1 < len(blob):
        length = blob[pos + 1]
        str_start = pos + 2
    # Four-byte length: 0x84 followed by 4 bytes big-endian
    elif byte == 0x84 and pos + 4 < len(blob):
        length = int.from_bytes(blob[pos + 1 : pos + 5], "big")
        str_start = pos + 5
    else:
        return None

    if length <= 0 or length > 100_000:
        return None
    if str_start + length > len(blob):
        return None

    try:
        return blob[str_start : str_start + length].decode("utf-8")
    except UnicodeDecodeError:
        return None


def _scan_for_utf8_run(blob: bytes) -> str | None:
    """Fallback: find the longest UTF-8 text run in the blob."""
    best = ""
    i = 50
    while i < len(blob):
        run_start = i
        while i < len(blob):
            b = blob[i]
            if 32 <= b < 127 or b in (10, 13, 9) or b >= 0xC0:
                i += 1
            else:
                break
        if i > run_start:
            try:
                chunk = blob[run_start:i].decode("utf-8", errors="ignore").strip()
                if len(chunk) > len(best) and _looks_like_text(chunk):
                    best = chunk
            except Exception:
                pass
        i += 1
    return best if best else None


def _looks_like_text(s: str) -> bool:
    """Heuristic: does this string look like actual message text?"""
    if not s or len(s.strip()) == 0:
        return False
    printable = sum(1 for c in s if c.isprintable() or c in "\n\r\t")
    return printable / len(s) > 0.5


def _clean(text: str) -> str:
    """Clean extracted text: remove control chars, surrogates, and strip."""
    text = text.replace("\ufffc", "").replace("\x00", "").replace("\x01", "")
    # Remove surrogate characters that break JSON encoding
    text = text.encode("utf-8", errors="surrogatepass").decode("utf-8", errors="replace")
    text = text.strip()
    return text if text else ""
