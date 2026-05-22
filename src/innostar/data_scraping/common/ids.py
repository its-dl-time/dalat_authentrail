from __future__ import annotations

import hashlib
from typing import Any

from .text import clean_text


def make_id(*parts: Any, length: int | None = None) -> str:
    raw = "|".join(clean_text(part) for part in parts)
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    return digest[:length] if length else digest

