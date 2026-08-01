"""Flask API for Provenance Guard."""

from flask import Flask, jsonify, request


app = Flask(__name__)


@app.get("/")
def root():
    """Return a minimal service-status response."""
    return jsonify({"status": "ok"})


@app.post("/submit")
def submit():
    """Accept a content submission; detection will be added in a later step."""
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({"error": "Request body must be valid JSON."}), 400

    missing_fields = [field for field in ("text", "creator_id") if field not in data]
    if missing_fields:
        return jsonify({"error": "Missing required fields: " + ", ".join(missing_fields)}), 400

    return jsonify(
        {
            "creator_id": data["creator_id"],
            "confidence_score": 0.50,
            "label": "Uncertain",
            "status": "received",
        }
    )


if __name__ == "__main__":
    app.run(debug=True)
