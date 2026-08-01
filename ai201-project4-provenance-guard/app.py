"""Flask API for Provenance Guard."""

from uuid import uuid4

from flask import Flask, jsonify, request

from audit import get_log, log_submission
from detector import DetectionError, assess_predictability, attribution_from_predictability_score

app = Flask(__name__)


@app.get("/")
def root():
    """Return a minimal service-status response."""
    return jsonify({"status": "ok"})


@app.post("/submit")
def submit():
    """Assess a submission with Signal 1 and return placeholder final results."""
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({"error": "Request body must be valid JSON."}), 400

    missing_fields = [field for field in ("text", "creator_id") if field not in data]
    if missing_fields:
        return jsonify({"error": "Missing required fields: " + ", ".join(missing_fields)}), 400

    try:
        signal_1 = assess_predictability(data["text"])
        attribution = attribution_from_predictability_score(signal_1["predictability_score"])
    except (DetectionError, ValueError) as error:
        return jsonify({"error": str(error)}), 503

    response = {
        "content_id": str(uuid4()),
        "creator_id": data["creator_id"],
        "attribution": attribution,
        "signal_1": signal_1,
        "confidence": 0.50,
        "confidence_score": 0.50,
        "label": "Uncertain",
        "status": "received",
    }
    log_submission(
        {
            "content_id": response["content_id"],
            "creator_id": response["creator_id"],
            "attribution": response["attribution"],
            "confidence": response["confidence"],
            "llm_score": signal_1["predictability_score"],
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
