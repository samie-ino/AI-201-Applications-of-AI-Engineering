# Provenance Guard

Provenance Guard is a Flask API that evaluates text using two independent
signals: a Groq-based predictability assessment and local stylometric
burstiness heuristics. Their equally weighted scores produce a human-authorship
confidence score, a transparency label, and an audit record.

## Run locally

```bash
pip install -r requirements.txt
flask --app app run
```

Set `GROQ_API_KEY` in `.env` before submitting text. The API provides `POST
/submit`, `POST /appeal`, and `GET /log`.

## Rate limiting

`POST /submit` is limited per client IP to **10 submissions per minute** and
**100 submissions per day**, using Flask-Limiter's in-memory local-development
storage.

Ten submissions per minute permits a writer to submit revisions or several
documents without friction, while stopping a high-speed script from using the
Groq-backed signal as an unbounded bulk-classification service. The daily cap
supports normal personal use while containing cost and abuse over longer runs.

### Verification

The 12-request rate-limit test produced the following status codes (the first
10 requests succeeded and the final 2 were rejected):

```text
200
200
200
200
200
200
200
200
200
200
429
429
```

## Audit log

`logs/audit.jsonl` is a structured JSONL audit trail. Each submission records
its timestamp, content ID, creator ID, attribution, combined confidence,
`llm_score`, `burstiness_score`, label, and status. The log contains multiple
submission entries, including an appealed submission marked `under_review`;
appeals are also recorded as separate linked events with their creator
reasoning. `GET /log` returns recent entries for documentation and grading.
