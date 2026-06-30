"""Tiny JSON-file-backed storage for Provenance Guard.

Two append-only-ish JSON files live next to this module:
  - audit_log.json    structured audit entries (one per submission/appeal event)
  - submissions.json  the full record for each content_id (needed by appeals in M5)

This is deliberately simple for the prototype. A real system would use a database
with proper concurrency control and access auth.
"""

import hashlib
import json
import os

_DIR = os.path.dirname(os.path.abspath(__file__))
_AUDIT_FILE = os.path.join(_DIR, "audit_log.json")
_SUBMISSIONS_FILE = os.path.join(_DIR, "submissions.json")


def _load(path):
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (json.JSONDecodeError, OSError):
        return []


def _save(path, data):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)


def hash_text(text):
    """Store a hash of the submitted text, never the raw text (planning.md)."""
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


# --- audit log ---------------------------------------------------------------

def append_audit(entry):
    log = _load(_AUDIT_FILE)
    log.append(entry)
    _save(_AUDIT_FILE, log)
    return entry


def get_log(limit=20):
    """Return the most recent `limit` audit entries (newest last)."""
    log = _load(_AUDIT_FILE)
    return log[-limit:]


# --- submissions -------------------------------------------------------------

def save_submission(record):
    subs = _load(_SUBMISSIONS_FILE)
    subs.append(record)
    _save(_SUBMISSIONS_FILE, subs)
    return record


def get_submission(content_id):
    for rec in _load(_SUBMISSIONS_FILE):
        if rec.get("content_id") == content_id:
            return rec
    return None
