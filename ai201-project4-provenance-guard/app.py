"""Provenance Guard — Flask app.

Milestone 3 scope:
  POST /submit  -> run Signal 1 (Groq LLM fluency), store result + audit entry, respond
  GET  /log     -> recent audit-log entries (for transparency / grading visibility)
  GET  /health  -> liveness check

Confidence and label here are provisional (single-signal). The real multi-signal
combiner and the three transparency-label variants arrive in M4 / M5.
"""

import datetime
import uuid

from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

load_dotenv()

import detector
import store

app = Flask(__name__)
limiter = Limiter(get_remote_address, app=app, default_limits=[])

# Provisional, human-readable label text per band (full M5 variants come later).
_LABEL_TEXT = {
    "likely_human": "Likely human-written (provisional, single signal).",
    "uncertain": "Uncertain — inconclusive (provisional, single signal).",
    "likely_ai": "Likely AI-generated (provisional, single signal).",
}


def _now():
    return (
        datetime.datetime.now(datetime.timezone.utc)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z")
    )


@app.post("/submit")
@limiter.limit("30 per minute")
def submit():
    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()
    creator_id = (data.get("creator_id") or "").strip()

    if not text:
        return jsonify({"error": "bad_request", "detail": "'text' is required"}), 400
    if not creator_id:
        return jsonify({"error": "bad_request", "detail": "'creator_id' is required"}), 400

    content_id = str(uuid.uuid4())
    timestamp = _now()

    signal1 = detector.llm_fluency(text)
    if signal1 is None:
        # Signal unavailable -> Uncertain, zero confidence (planning.md §2 fallback).
        llm_score = None
        attribution = "uncertain"
        confidence = 0.0
        llm_reason = "LLM signal unavailable."
    else:
        llm_score = round(signal1["score"], 3)
        attribution = detector.attribution_from_score(llm_score)
        # Provisional single-signal confidence, capped at 0.5 until the M4 combiner.
        confidence = round(min(0.5, abs(llm_score - 0.5) * 2), 3)
        llm_reason = signal1["reason"]

    record = {
        "content_id": content_id,
        "creator_id": creator_id,
        "timestamp": timestamp,
        "text_hash": store.hash_text(text),
        "attribution": attribution,
        "confidence": confidence,
        "llm_score": llm_score,
        "llm_reason": llm_reason,
        "label": _LABEL_TEXT[attribution],
        "status": "classified",
    }
    store.save_submission(record)

    # Structured audit entry (planning.md: hash, not raw text).
    store.append_audit(
        {
            "content_id": content_id,
            "creator_id": creator_id,
            "timestamp": timestamp,
            "attribution": attribution,
            "confidence": confidence,
            "llm_score": llm_score,
            "status": "classified",
        }
    )

    return (
        jsonify(
            {
                "content_id": content_id,
                "creator_id": creator_id,
                "timestamp": timestamp,
                "attribution": attribution,
                "confidence": confidence,
                "label": _LABEL_TEXT[attribution],
                "signals": {"llm_fluency": llm_score},
                "llm_reason": llm_reason,
                "status": "classified",
            }
        ),
        200,
    )


@app.get("/log")
def get_log():
    limit = request.args.get("limit", default=20, type=int)
    return jsonify({"entries": store.get_log(limit)})


@app.get("/health")
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
