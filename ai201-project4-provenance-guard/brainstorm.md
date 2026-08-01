# Brainstorming & API Sketch

## 1. The False Positive Scenario
**Scenario:** A human creator submits a highly structured, formal product manual.
Because the text is formal (low perplexity) and methodical (low burstiness), the Scoring Engine evaluates the signals and returns a confidence score of **0.58** (leaning AI, but highly uncertain). 

Instead of slapping a definitive "AI-Generated" stamp on it, the Label Generator sees the 0.58 score and outputs the "Uncertain" label: *"This content shows mixed signals and cannot be definitively classified as human or AI."* 

The creator sees this label and feels their work is being unfairly doubted. They use the platform's UI to trigger a `POST /appeal` request, submitting their reasoning ("This is a technical manual, so the language is strictly standardized"). The system receives the appeal, links it to the original submission ID in the **Audit Log**, and changes the submission's status to `"Under Review"`.

## 2. API Surface Sketch
Here is the contract that the code will implement:

### `POST /submit`
*   **Accepts:** 
    {
      "author_id": "string",
      "text_content": "string"
    }
*   **Returns (200 OK):**
    {
      "submission_id": "string",
      "attribution": "AI" | "Human" | "Uncertain",
      "confidence_score": 0.00,
      "transparency_label": "string"
    }
*(Note: Returns 429 Too Many Requests if rate limit is exceeded).*

### `POST /appeal`
*   **Accepts:**
    {
      "submission_id": "string",
      "creator_reasoning": "string"
    }
*   **Returns (200 OK):**
    {
      "submission_id": "string",
      "status": "Under Review",
      "message": "Appeal successfully logged."
    }

### `GET /log`
*   **Accepts:** Nothing (or an optional `?limit=10` parameter).
*   **Returns (200 OK):**
    [
      {
        "submission_id": "string",
        "timestamp": "ISO-8601",
        "signals": {"predictability": 0.8, "burstiness": 0.4},
        "confidence_score": 0.6,
        "label_issued": "string",
        "status": "Final" | "Under Review",
        "appeal_reason": "string (if any)"
      }
    ]