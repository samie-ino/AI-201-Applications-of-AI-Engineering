# Brainstorming & API Sketch

*This is my Milestone 1 brainstorming file, written before any code existed.
The scenario in Section 1 still holds up. The API sketch in Section 2 was my
first guess at field names and shapes — the real implementation (see
`README.md` and `app.py`) diverged in several places once I was actually
wiring up Flask, so Section 2 below has been updated to match what shipped,
with the original guess struck through for reference.*

## 1. The False Positive Scenario
**Scenario:** A human creator submits a highly structured, formal product manual.
Because the text is formal (low perplexity) and methodical (low burstiness), the Scoring Engine evaluates the signals and returns a confidence score of **0.58** (leaning AI, but highly uncertain). 

Instead of slapping a definitive "AI-Generated" stamp on it, the Label Generator sees the 0.58 score and outputs the "Uncertain" label: *"This content shows mixed signals and cannot be definitively classified as human or AI."* 

The creator sees this label and feels their work is being unfairly doubted. They use the platform's UI to trigger a `POST /appeal` request, submitting their reasoning ("This is a technical manual, so the language is strictly standardized"). The system receives the appeal, links it to the original submission ID in the **Audit Log**, and changes the submission's status to `"Under Review"`.

*(This scenario matches reality closely — a 0.58 score really does land in the "Uncertain" band, 0.36–0.65. The one field-level detail that changed: the actual status value is the lowercase `"under_review"`, not `"Under Review"`.)*

## 2. API Surface Sketch

### Original guess (pre-implementation)

*   `POST /submit` accepted `{"author_id", "text_content"}` and returned
    `{"submission_id", "attribution": "AI"|"Human"|"Uncertain", "confidence_score", "transparency_label"}`.
*   `POST /appeal` accepted `{"submission_id", "creator_reasoning"}` and
    returned `{"submission_id", "status": "Under Review", "message": "Appeal successfully logged."}`.
*   `GET /log` returned a bare JSON array of log entries, each with
    `"submission_id"`, `"signals": {"predictability", "burstiness"}`,
    `"label_issued"`, and `"status": "Final"|"Under Review"`.

### As actually implemented

`POST /submit`
*   **Accepts:** `{"text": "string", "creator_id": "string"}`
*   **Returns (200 OK):**
    ```json
    {
      "content_id": "uuid",
      "creator_id": "string",
      "attribution": "likely_ai" | "uncertain" | "likely_human",
      "signal_1": {"predictability_score": 0.0, "reasoning": "string"},
      "signal_2": {"burstiness_score": 0.0, "sentence_length_variation": 0.0, "clause_structure_variation": 0.0, "type_token_ratio": 0.0},
      "confidence": 0.0,
      "confidence_score": 0.0,
      "label": "High-Confidence AI" | "Uncertain" | "High-Confidence Human",
      "transparency_label": "string",
      "status": "classified"
    }
    ```
*   Returns `429` if the rate limit is exceeded, as planned.

`POST /appeal`
*   **Accepts:** `{"content_id": "string", "creator_reasoning": "string"}`
*   **Returns (200 OK):** `{"content_id": "string", "status": "under_review"}`
    — no `message` field; the status change itself is the confirmation.

`GET /log`
*   **Accepts:** nothing (no `limit` query param currently).
*   **Returns (200 OK):** `{"entries": [...]}` — each entry is a flat
    submission or appeal record straight from `logs/audit.jsonl` (see
    `README.md`'s Audit Log section for the exact fields), not the nested
    `"signals"` shape originally sketched.

The naming changed mostly for consistency with the audit log: `content_id`/
`creator_id` read more clearly once they're sitting next to log fields like
`llm_score` and `burstiness_score`, and lowercase `likely_ai`/`uncertain`/
`likely_human` values are easier to branch on in code than mixed-case
strings. The exposed signal breakdown (`signal_1`/`signal_2` with their
sub-scores) wasn't in the original sketch at all — I added it once I
realized a creator appealing a decision would want to see *why* each signal
scored the way it did, not just the combined number.