# Provenance Guard

Provenance Guard is a Flask API that assesses whether submitted text was
likely written by a human or an AI tool. It combines two independent
detection signals into a single confidence score, maps that score to a
plain-language transparency label, records every decision in a structured
audit log, and lets creators appeal a classification they believe is wrong.

## Run locally

```bash
pip install -r requirements.txt
flask --app app run
```

Set `GROQ_API_KEY` in `.env` before submitting text. The API provides `POST
/submit`, `POST /appeal`, and `GET /log`.

## Architecture

```
Client
  │  POST /submit {text, creator_id}
  ▼
Rate Limiter (Flask-Limiter, per-IP) ──(over limit)──> 429
  │
  ▼
Detection Pipeline
  ├── Signal 1: Predictability (Groq LLM-as-judge)  ──┐
  └── Signal 2: Burstiness (local stylometric heuristics) ──┤
                                                            ▼
                                                  Scoring Engine (50/50 average)
                                                            │
                                                            ▼
                                                  Label Generator (3 bands)
                                                            │
                                                            ▼
                                                  Audit Logger (logs/audit.jsonl)
                                                            │
                                                            ▼
                                                  Client Response
```

An appeal (`POST /appeal {content_id, creator_reasoning}`) looks up the
matching submission in the audit log, flips its status to
`"under_review"`, and appends a second, linked `record_type: "appeal"`
entry carrying the creator's reasoning. `GET /log` returns recent entries
from the same file for documentation and grading.

## Detection signals

**Signal 1 — Predictability (Groq, LLM-as-judge).** A Groq call
(`llama-3.3-70b-versatile`) is asked to estimate how statistically
predictable the text's word choices are, returning a score from `0.0`
(highly predictable) to `1.0` (highly unpredictable). This is the same
LLM-as-judge pattern as a classifier: instead of generating end-user text,
the model evaluates input. I chose an LLM for this signal because
predictability is fundamentally a language-modeling judgment — "how
surprising is this word given what came before" is exactly what an LLM is
already calibrated to estimate, and it's far cheaper to prompt for a score
than to stand up a local perplexity model against the same reference
distribution.

**Signal 2 — Burstiness (local stylometric heuristics, no API call).**
Pure Python measures sentence-length variation (60%), clause-structure
variation (25%, via punctuation and conjunction density), and lexical
diversity / type-token ratio (15%). This signal exists specifically
*because* it doesn't depend on an LLM: it's deterministic, free, instant,
and — critically — measures something structurally different from Signal
1. Predictability looks at word-level choices; burstiness looks at
sentence-level rhythm. AI text tends to be uniform on both axes, but a
system that only checked word predictability could be fooled by
paraphrasing tools that shuffle vocabulary while still producing
metronomic sentence structure. Two signals that can fail independently
are more informative than a single signal checked twice.

**Why average them 50/50 instead of something more elaborate?** An equal
weighting is the simplest defensible choice when there's no labeled dataset
to justify weighting one signal more than the other, and it keeps the
score interpretable: a submission that is ambiguous on one axis and clear
on the other lands near the middle, which is the honest thing to report
rather than a confident-looking number produced by an arbitrary weighting
scheme.

**What I'd change for a real deployment.** I would not ship the 50/50
average as-is. It should be calibrated against a labeled corpus of known
human and known AI text so the weighting (and the label thresholds) reflect
which signal is actually more predictive, rather than an assumption made
before any real data existed. I'd also add a third, independent signal —
something like model-family fingerprinting or metadata/provenance checks
(C2PA content credentials, generation metadata) — because two signals that
both key off "uniformity of writing style" can still be defeated together
by the same countermeasure (see Known Limitations below). Finally, Signal
1 currently fails closed with a `503` if Groq is unreachable or returns a
malformed response; in production I'd want a documented fallback (e.g.,
score on burstiness alone with a visibly lower-confidence label) rather
than rejecting the submission outright.

## Confidence scoring — example submissions

These two submissions were sent to a running local instance during testing
and show the scoring producing meaningfully different, non-constant
output:

**Higher-confidence case** — a short, uniform, repetitive passage:

> "The system processes data. The system validates input. The system
> returns output. The system logs the result."

```json
{
  "signal_1": { "predictability_score": 0.10 },
  "signal_2": { "burstiness_score": 0.17 },
  "confidence": 0.14,
  "attribution": "likely_ai",
  "label": "High-Confidence AI"
}
```

**Lower-confidence ("uncertain") case** — a structured maintenance
procedure with more sentence-length and clause variety, similar to the
technical-manual edge case anticipated in planning:

> "Section 4.2 covers routine maintenance procedures for the unit.
> Technicians should inspect the filter monthly and replace it if visibly
> soiled. Do not skip this step — a clogged filter reduces airflow and can
> trip the thermal cutoff, which is annoying to reset. Lubricate the
> bearing assembly per the schedule in Table 3. If unusual noise persists
> after lubrication, escalate to a senior technician rather than continuing
> to operate the unit."

```json
{
  "signal_1": { "predictability_score": 0.20 },
  "signal_2": { "burstiness_score": 0.56 },
  "confidence": 0.38,
  "attribution": "uncertain",
  "label": "Uncertain"
}
```

The gap between `0.14` and `0.38` — and the corresponding shift from a
"High-Confidence AI" label to an "Uncertain" one — comes entirely from
Signal 2: both passages score low on predictability (formal, standardized
language), but the second passage's warnings and clause-heavy sentences
push its burstiness more than 3x higher than the first, which is enough to
move the combined score out of the AI band.

## Transparency label variants

All three label variants exist as fixed text in `labels.py`, keyed to the
combined confidence score:

**High-Confidence AI** (score `0.00`–`0.35`):
> "This content was likely generated by an AI tool. Our systems detected
> highly predictable language patterns and uniform sentence structures
> typical of machine generation."

**Uncertain** (score `0.36`–`0.65`):
> "This content shows mixed signals. It contains structural patterns
> common to both human writers and AI tools, so we cannot make a
> definitive classification."

**High-Confidence Human** (score `0.66`–`1.00`):
> "This content was likely written by a human. Our systems detected
> natural variations in sentence structure and vocabulary."

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

## Known limitations

The signals in this system both measure *stylistic uniformity* — one at
the word-choice level, one at the sentence-structure level — which means
they share a common blind spot: **formal, standardized human writing that
is required to be uniform will be misclassified as AI-generated.** A
technical manual, a legal brief, or a standard operating procedure uses
deliberately narrow, repeated vocabulary (low predictability) and
methodical, evenly-paced sentences (low burstiness) *because that is what
correctness looks like in that genre* — not because a human didn't write
it. The maintenance-procedure example above scored `0.38` ("Uncertain")
specifically because it sits close to this edge, and a slightly more
repetitive real manual would likely cross into "High-Confidence AI." This
isn't a data-volume problem; it's a structural property of the two
signals, both of which treat uniformity as evidence of machine authorship.
A production system would need a genre-aware baseline (comparing against
typical burstiness for technical writing specifically, not writing in
general) rather than one fixed threshold for all text.

## Spec reflection

**Where the spec helped:** `planning.md`'s decision to define the three
label thresholds and their exact wording *before* any scoring code was
written meant the label generator (`labels.py`) and the scoring engine
(`combine_signal_scores`) never had to guess at a boundary — the 0.35/0.65
cutoffs were fixed in advance and the code just had to implement them
faithfully, which kept the "what does 0.60 mean" ambiguity from leaking
into the implementation.

**Where the implementation diverged from the plan:** `brainstorm.md` was a
pre-implementation sketch, not a locked contract, so several of its field
names didn't survive contact with the real Flask app. It proposed
`submission_id`/`author_id` and a three-way `attribution` of
`"AI"|"Human"|"Uncertain"`; the shipped API uses `content_id`/`creator_id`
and lowercase, code-friendly values (`likely_ai`, `uncertain`,
`likely_human`) that read better sitting next to audit-log fields like
`llm_score` and `burstiness_score`. The bigger divergence: the sketch's
`/submit` response only returned the combined score and label, but the
shipped response also exposes each signal's sub-scores (`signal_1`,
`signal_2`) individually. I added that once it was clear an appealing
creator needs to see *why* each signal scored the way it did, not just the
final number — the reviewer view described in `planning.md`'s appeals
workflow section requires exactly this breakdown. See `brainstorm.md` for
the full before/after comparison.

## AI usage

**Instance 1 — Flask skeleton and Signal 1 generation.** I directed the AI
to generate the initial Flask application skeleton and the first detection
signal, giving it the full architecture narrative (rate limiter → detection
pipeline → scoring engine → label generator → audit logger) plus the exact
spec for Signal 1 (0.0–1.0 predictability, highly predictable to highly
unpredictable) from `planning.md`. It produced
`calculate_predictability_score`, a `POST /submit` skeleton, and a basic
JSON audit logger.

**Instance 2 — Debugging the Flask setup.** When I first tried running the
app, it didn't come up cleanly — I ran into errors on startup instead of a
working server. I used AI to help me work through the Flask setup and fix
those errors, going back and forth until `flask run` started successfully
and hitting the root endpoint returned `{"status": "ok"}`, confirming the
server was actually running correctly.
