"""Flask API for Provenance Guard."""

from uuid import uuid4

from flask import Flask, jsonify, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from audit import get_log, log_submission, update_submission_for_appeal
from detector import (
    DetectionError,
    assess_burstiness,
    assess_predictability,
    combine_signal_scores,
)

app = Flask(__name__)
limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    default_limits=[],
    storage_uri="memory://",
)


@app.get("/")
def root():
    """Return a minimal service-status response."""
    return jsonify({"status": "ok"})


@app.post("/submit")
@limiter.limit("10 per minute; 100 per day")
def submit():
    """Assess a submission with both signals and return their combined result."""
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({"error": "Request body must be valid JSON."}), 400

    missing_fields = [field for field in ("text", "creator_id") if field not in data]
    if missing_fields:
        return jsonify({"error": "Missing required fields: " + ", ".join(missing_fields)}), 400

    try:
        signal_1 = assess_predictability(data["text"])
        signal_2 = assess_burstiness(data["text"])
        combined = combine_signal_scores(
            signal_1["predictability_score"], signal_2["burstiness_score"]
        )
    except (DetectionError, ValueError) as error:
        return jsonify({"error": str(error)}), 503

    response = {
        "content_id": str(uuid4()),
        "creator_id": data["creator_id"],
        "attribution": combined["attribution"],
        "signal_1": signal_1,
        "signal_2": signal_2,
        "confidence": combined["confidence"],
        "confidence_score": combined["confidence"],
        "label": combined["label"],
        "transparency_label": combined["message"],
        "status": "classified",
    }
    log_submission(
        {
            "record_type": "submission",
            "content_id": response["content_id"],
            "creator_id": response["creator_id"],
            "text": data["text"],
            "attribution": response["attribution"],
            "confidence": response["confidence"],
            "llm_score": signal_1["predictability_score"],
            "burstiness_score": signal_2["burstiness_score"],
            "label": response["label"],
            "transparency_label": response["transparency_label"],
            "status": "classified",
        }
    )
    return jsonify(response)


@app.post("/appeal")
def appeal():
    """Place a prior submission under review and record the creator's appeal."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Request body must be valid JSON."}), 400

    missing_fields = [field for field in ("content_id", "creator_reasoning") if field not in data]
    if missing_fields:
        return jsonify({"error": "Missing required fields: " + ", ".join(missing_fields)}), 400
    if not isinstance(data["creator_reasoning"], str) or not data["creator_reasoning"].strip():
        return jsonify({"error": "creator_reasoning must be a non-empty string."}), 400

    if not update_submission_for_appeal(data["content_id"], data["creator_reasoning"].strip()):
        return jsonify({"error": "Submission not found."}), 404
    return jsonify({"content_id": data["content_id"], "status": "under_review"})


@app.get("/log")
def log():
    """Return recent audit-log entries for documentation and grading."""
    return jsonify({"entries": get_log()})


@app.errorhandler(429)
def rate_limit_exceeded(error):
    """Return rate-limit failures in the API's JSON format."""
    return jsonify({"error": "Rate limit exceeded. Please try again later."}), 429


if __name__ == "__main__":
    app.run(debug=True)
