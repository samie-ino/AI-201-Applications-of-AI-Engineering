"""Flask API for Provenance Guard."""

from uuid import uuid4

from flask import Flask, jsonify, request

from audit import get_log, log_submission
from detector import (
    DetectionError,
    assess_burstiness,
    assess_predictability,
    combine_signal_scores,
)

app = Flask(__name__)


@app.get("/")
def root():
    """Return a minimal service-status response."""
    return jsonify({"status": "ok"})


@app.post("/submit")
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
        "status": "classified",
    }
    log_submission(
        {
            "content_id": response["content_id"],
            "creator_id": response["creator_id"],
            "attribution": response["attribution"],
            "confidence": response["confidence"],
            "llm_score": signal_1["predictability_score"],
            "burstiness_score": signal_2["burstiness_score"],
            "status": "classified",
        }
    )
    return jsonify(response)


@app.get("/log")
def log():
    """Return recent audit-log entries for documentation and grading."""
    return jsonify({"entries": get_log()})


if __name__ == "__main__":
    app.run(debug=True)
