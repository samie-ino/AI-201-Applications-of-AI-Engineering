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
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=[],
    storage_uri="memory://",
)


def _now():
    return (
        datetime.datetime.now(datetime.timezone.utc)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z")
    )


@app.post("/submit")
@limiter.limit("10 per minute;100 per day")
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
    label = detector.build_label(result)  # one of the three variants (planning.md §3)

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
        "label": label,
        "status": "classified",
        "appealed": False,
    }
    store.save_submission(record)

    # Structured audit entry — captures BOTH signals + the combined score.
    store.append_audit(
        {
            "event": "classified",
            "content_id": content_id,
            "creator_id": creator_id,
            "timestamp": timestamp,
            "attribution": attribution,
            "confidence": result["confidence"],
            "combined_score": result["combined_score"],
            "llm_score": result["llm_score"],
            "burstiness_score": result["burstiness_score"],
            "status": "classified",
            "appeal_filed": False,
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
                "label": label,
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


@app.post("/appeal")
@limiter.limit("10 per minute;100 per day")
def appeal():
    data = request.get_json(silent=True) or {}
    content_id = (data.get("content_id") or "").strip()
    # accept the milestone's field name, or planning.md's `reason` as an alias
    reasoning = (data.get("creator_reasoning") or data.get("reason") or "").strip()

    if not content_id:
        return jsonify({"error": "bad_request", "detail": "'content_id' is required"}), 400
    if not reasoning:
        return jsonify({"error": "bad_request", "detail": "'creator_reasoning' is required"}), 400

    sub = store.get_submission(content_id)
    if sub is None:
        return jsonify({"error": "not_found", "detail": "unknown content_id"}), 404

    # Idempotent: if this content was already appealed, return the existing appeal.
    existing = store.get_appeal_by_content(content_id)
    if existing is not None:
        return (
            jsonify(
                {
                    "message": "An appeal already exists for this content.",
                    "appeal_id": existing["appeal_id"],
                    "content_id": content_id,
                    "status": existing["status"],
                    "timestamp": existing["created_at"],
                }
            ),
            200,
        )

    appeal_id = str(uuid.uuid4())
    timestamp = _now()

    # Store the appeal with a snapshot of the original decision (reviewer queue).
    store.save_appeal(
        {
            "appeal_id": appeal_id,
            "content_id": content_id,
            "creator_id": sub.get("creator_id"),
            "appeal_reasoning": reasoning,
            "status": "under_review",
            "created_at": timestamp,
            "original_attribution": sub.get("attribution"),
            "original_confidence": sub.get("confidence"),
            "original_combined_score": sub.get("combined_score"),
            "llm_score": sub.get("llm_score"),
            "burstiness_score": sub.get("burstiness_score"),
            "text_hash": sub.get("text_hash"),
        }
    )

    # Flip the submission status and mark it appealed.
    store.update_submission(
        content_id,
        {"status": "under_review", "appealed": True, "appeal_id": appeal_id},
    )

    # Log the appeal ALONGSIDE the original classification decision.
    store.append_audit(
        {
            "event": "appeal_opened",
            "content_id": content_id,
            "appeal_id": appeal_id,
            "creator_id": sub.get("creator_id"),
            "timestamp": timestamp,
            "attribution": sub.get("attribution"),
            "confidence": sub.get("confidence"),
            "combined_score": sub.get("combined_score"),
            "llm_score": sub.get("llm_score"),
            "burstiness_score": sub.get("burstiness_score"),
            "status": "under_review",
            "appeal_filed": True,
            "appeal_reasoning": reasoning,
        }
    )

    return (
        jsonify(
            {
                "message": "Appeal received. Your submission is now under review.",
                "appeal_id": appeal_id,
                "content_id": content_id,
                "status": "under_review",
                "timestamp": timestamp,
            }
        ),
        200,
    )


@app.get("/appeals")
def appeals_queue():
    """Reviewer queue: every appeal with a snapshot of the original decision."""
    return jsonify({"appeals": store.get_appeals()})


@app.post("/appeal/<appeal_id>/resolve")
def resolve_appeal(appeal_id):
    data = request.get_json(silent=True) or {}
    decision = (data.get("decision") or "").strip().lower()
    note = (data.get("note") or "").strip()

    if decision not in ("upheld", "overturned"):
        return (
            jsonify(
                {"error": "bad_request", "detail": "'decision' must be 'upheld' or 'overturned'"}
            ),
            400,
        )

    appeal = store.get_appeal(appeal_id)
    if appeal is None:
        return jsonify({"error": "not_found", "detail": "unknown appeal_id"}), 404

    timestamp = _now()
    new_status = f"resolved_{decision}"
    store.update_appeal(
        appeal_id, {"status": new_status, "resolved_at": timestamp, "reviewer_note": note}
    )
    # 'overturned' means the original label was wrong -> mark human-corrected.
    sub_status = "human_corrected" if decision == "overturned" else "classified"
    store.update_submission(appeal["content_id"], {"status": sub_status})

    store.append_audit(
        {
            "event": "appeal_resolved",
            "content_id": appeal["content_id"],
            "appeal_id": appeal_id,
            "timestamp": timestamp,
            "decision": decision,
            "status": new_status,
            "reviewer_note": note,
        }
    )

    return jsonify(
        {
            "message": f"Appeal {decision}.",
            "appeal_id": appeal_id,
            "content_id": appeal["content_id"],
            "status": new_status,
            "timestamp": timestamp,
        }
    )


@app.get("/log")
def get_log():
    limit = request.args.get("limit", default=20, type=int)
    return jsonify({"entries": store.get_log(limit)})


@app.get("/health")
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)
