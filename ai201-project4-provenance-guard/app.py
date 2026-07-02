"""Provenance Guard — Flask app.

Scope so far:
  POST /submit  -> run both signals + combiner, store result + audit entry, respond
  GET  /log     -> recent audit-log entries (for transparency / grading visibility)
  GET  /health  -> liveness check

The three full transparency-label variants arrive in M5; label text here is provisional.
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
    "likely_human": "Likely human-written (provisional label).",
    "uncertain": "Uncertain — inconclusive (provisional label).",
    "likely_ai": "Likely AI-generated (provisional label).",
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

    # Run both signals + the confidence combiner (planning.md §1/§2).
    result = detector.analyze(text)
    attribution = result["attribution"]

    record = {
        "content_id": content_id,
        "creator_id": creator_id,
        "timestamp": timestamp,
        "text_hash": store.hash_text(text),
        "attribution": attribution,
        "confidence": result["confidence"],
        "combined_score": result["combined_score"],
        "llm_score": result["llm_score"],
        "burstiness_score": result["burstiness_score"],
        "agreement": result["agreement"],
        "flags": result["flags"],
        "llm_reason": result["llm_reason"],
        "label": _LABEL_TEXT[attribution],
        "status": "classified",
    }
    store.save_submission(record)

    # Structured audit entry — now captures BOTH signals + the combined score.
    store.append_audit(
        {
            "content_id": content_id,
            "creator_id": creator_id,
            "timestamp": timestamp,
            "attribution": attribution,
            "confidence": result["confidence"],
            "combined_score": result["combined_score"],
            "llm_score": result["llm_score"],
            "burstiness_score": result["burstiness_score"],
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
                "confidence": result["confidence"],
                "combined_score": result["combined_score"],
                "label": _LABEL_TEXT[attribution],
                "signals": {
                    "llm_fluency": result["llm_score"],
                    "burstiness": result["burstiness_score"],
                },
                "agreement": result["agreement"],
                "flags": result["flags"],
                "llm_reason": result["llm_reason"],
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
