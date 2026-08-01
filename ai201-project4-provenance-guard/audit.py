"""Structured audit logging for Provenance Guard submissions and appeals."""

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


def update_submission_for_appeal(content_id: str, creator_reasoning: str) -> bool:
    """Mark a submission under review and append its corresponding appeal event."""
    if not AUDIT_LOG.exists():
        return False

    entries = [
        json.loads(line)
        for line in AUDIT_LOG.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    for entry in reversed(entries):
        if entry.get("content_id") != content_id or entry.get("record_type", "submission") != "submission":
            continue
        entry["status"] = "under_review"
        entry["appeal_reasoning"] = creator_reasoning
        entry["appealed_at"] = datetime.now(timezone.utc).isoformat()
        AUDIT_LOG.write_text(
            "".join(json.dumps(updated_entry) + "\n" for updated_entry in entries),
            encoding="utf-8",
        )
        log_submission(
            {
                "record_type": "appeal",
                "content_id": content_id,
                "creator_reasoning": creator_reasoning,
                "status": "under_review",
            }
        )
        return True
    return False


def get_log(limit: int = 50) -> list[dict[str, Any]]:
    """Return up to *limit* of the most recent valid audit-log entries."""
    if not AUDIT_LOG.exists():
        return []

    entries = []
    for line in AUDIT_LOG.read_text(encoding="utf-8").splitlines():
        if line.strip():
            entries.append(json.loads(line))
    return entries[-limit:]
