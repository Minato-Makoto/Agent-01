"""
Tool-call ID normalization utilities.
"""

import hashlib
import re
from typing import Dict


_ALNUM_RE = re.compile(r"[^a-zA-Z0-9]")


def sanitize_tool_call_id(raw_id: str, mode: str = "strict") -> str:
    """
    Sanitize tool call ID for strict providers.

    Modes:
    - strict: alphanumeric only
    - strict9: alphanumeric exactly 9 chars
    """
    if not isinstance(raw_id, str) or not raw_id:
        return "defaultid" if mode == "strict9" else "defaulttoolid"

    cleaned = _ALNUM_RE.sub("", raw_id)
    if not cleaned:
        cleaned = "sanitized"

    if mode == "strict9":
        if len(cleaned) >= 9:
            return cleaned[:9]
        digest = hashlib.sha1(cleaned.encode("utf-8")).hexdigest()[:9]
        return digest

    return cleaned


def remap_tool_call_ids(ids: Dict[str, str], mode: str = "strict") -> Dict[str, str]:
    """
    Build stable remapping with collision avoidance.
    """
    used = set()
    out: Dict[str, str] = {}
    for original in ids.keys():
        base = sanitize_tool_call_id(original, mode=mode)
        candidate = base
        if candidate in used:
            suffix = hashlib.sha1(original.encode("utf-8")).hexdigest()[:6]
            if mode == "strict9":
                candidate = (base[:3] + suffix)[:9]
            else:
                candidate = f"{base}{suffix}"
        used.add(candidate)
        out[original] = candidate
    return out
