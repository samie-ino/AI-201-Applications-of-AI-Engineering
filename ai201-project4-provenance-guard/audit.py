"""Append-only audit logging for Provenance Guard submissions."""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


AUDIT_LOG = Path(__file__).parent / "logs" / "audit.jsonl"


def log_submission(record: dict[str, Any]) -> None:
    """Append a submission record as one JSON object per line."""
    AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
    entry = {"timestamp": datetime.now(timezone.utc).isoformat(), **record}
    with AUDIT_LOG.open("a", encoding="utf-8") as log_file:
        log_file.write(json.dumps(entry) + "\n")


def get_log(limit: int = 50) -> list[dict[str, Any]]:
    """Return up to *limit* of the most recent valid audit-log entries."""
    if not AUDIT_LOG.exists():
        return []

    entries = []
    for line in AUDIT_LOG.read_text(encoding="utf-8").splitlines():
        if line.strip():
            entries.append(json.loads(line))
    return entries[-limit:]
