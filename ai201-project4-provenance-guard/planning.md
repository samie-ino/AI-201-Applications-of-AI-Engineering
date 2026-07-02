# Provenance Guard — Planning & Spec

Provenance Guard accepts a piece of text, runs it through two independent detection
signals, blends them into a single calibrated AI-likelihood score, and returns a
**transparency label** that is always probabilistic, always shows its work, and is
always contestable through an appeals flow. This document is the spec all code is built
against, and the source I hand (section by section) to AI tools in Milestones 3–5.

Stack: Flask + flask-limiter (rate limiting) + Groq (LLM signal). Storage for the
prototype is in-memory; the audit log is append-only.

---

## 1. Detection signals

I chose one **cheap, deterministic, structural** signal and one **richer, semantic**
signal so they fail in *different* ways. When two independent detectors disagree, that
disagreement lowers confidence rather than being averaged away.

### Signal 1 — LLM fluency / perplexity judgment — Groq *(implemented first, M3)*

- **Measures:** how formulaic and low-surprise the phrasing is (even tone, hedging,
  formulaic transitions like "Moreover," / "In conclusion,", absence of personal voice).
- **Why it separates human vs AI:** AI samples high-probability tokens → unusually
  smooth, low-perplexity prose. Humans use more surprising, idiosyncratic, lower-
  probability word choices and rough edges.
- **Output shape:** the Groq prompt asks for a strict JSON object
  `{"ai_likelihood": <int 0-100>, "reason": <short str>}`. I normalize:
  `s1 = ai_likelihood / 100`. If the call fails or returns unparseable output, `s1` is
  marked `null` and the combiner falls back to Signal 2 alone (and confidence is
  capped — see §2).
- **Blind spot:** a fluent or AI-edited human text reads smoothly and is flagged. The
  judge is itself probabilistic — confidently wrong at times, prompt-gameable, weaker on
  short text and on under-represented domains/languages, and may invent a plausible
  rationale for a wrong score.
- **Why it's the first signal:** it produces a usable score even on short text, so it
  gives a clean end-to-end demo in M3 before the structural signal is added in M4.

### Signal 2 — Burstiness (sentence-length variation) — local Python *(added M4)*

- **Measures:** the coefficient of variation (CV) of sentence lengths in words —
  `CV = stdev(sentence_lengths) / mean(sentence_lengths)`.
- **Why it separates human vs AI:** humans are "bursty" — they mix short punchy
  sentences with long winding ones, so CV is high. LLMs decode high-probability
  continuations and tend to produce evenly-paced, uniform sentences, so CV is low.
- **Output shape:** a float `s2 ∈ [0,1]` = P(AI). Calibration from raw CV:
  `s2 = clamp(1 - (CV / 0.60), 0, 1)`. So CV ≥ 0.60 → s2 = 0 (very human); CV = 0.30 →
  s2 = 0.5; CV = 0 → s2 = 1.0 (perfectly uniform → AI-like). `0.60` is the reference
  CV I'll sanity-check against sample human text in M4 and adjust if needed.
- **Blind spot:** blind to meaning and register. Formal/templated human writing (lab
  reports, legal boilerplate, ESL writing with simple uniform sentences) has low CV and
  is wrongly flagged AI. Unreliable on short text (can't estimate variance from 2
  sentences — this is why the M3 demo text uses the LLM signal). Trivially defeated by
  deliberately varying sentence length.

### Combining the two signals

```
s1 = LLM fluency, s2 = burstiness, both ∈ [0,1]   (P that text is AI; 1 = most AI-like)

combined_score = 0.6 * s1 + 0.4 * s2          # LLM weighted higher (richer signal)
agreement      = 1 - abs(s1 - s2)             # 1 = perfect agreement, 0 = opposite
confidence     = round(combined distance from 0.5, agreement-adjusted)  # see §2
```

If `s1` is `null` (Groq failed): `combined_score = s2`, and the result is forced into
the **Uncertain** band with a note that only one signal was available.

---

## 2. Uncertainty representation

**What `combined_score = 0.6` means to the system:** it is the blended probability that
the text is AI-generated — a 60% lean toward AI. By itself that is *not enough* to
declare "AI": 0.6 sits inside the Uncertain band (see thresholds), so the system reports
"leaning AI, but inconclusive." This is exactly the number I need to be able to explain
to a non-technical user without it sounding like a verdict.

**Calibration (raw → score):** each signal is mapped to `[0,1]` at the signal level
(Signal 1 via `/100`; Signal 2 via the CV formula in §1). I am not claiming these are
true probabilities — they are *calibrated bands*, and the thresholds below are where the
real meaning lives. I will eyeball-calibrate the CV reference and the band edges in M4
against a handful of clearly-human and clearly-AI samples.

**Confidence (separate from the AI-likelihood score):** confidence answers "how much
should you trust this label," and is driven by two things — how far the combined score
is from the 0.5 coin-flip, and how much the two signals agree:

```
confidence = clamp( (abs(combined_score - 0.5) * 2) * (0.5 + 0.5 * agreement), 0, 1 )
```

So a clear, agreed result (e.g. s1=0.9, s2=0.85) yields high confidence; a split
decision (s1=0.1, s2=0.9 → combined 0.58) yields *low* confidence even though the score
isn't near 0.5. Single-signal results (one signal `null`) have confidence capped at 0.5.

**Thresholds — three bands, not a binary flip at 0.5:**

| combined_score | Band | Override |
|---|---|---|
| `0.00 – 0.35` | **Likely human** | — |
| `0.35 – 0.65` | **Uncertain** | — |
| `0.65 – 1.00` | **Likely AI** | — |
| any | **forced Uncertain** | if `abs(s1 - s2) > 0.40` (signals strongly disagree) **or** either signal is `null` **or** text fails the length gate (§5) |

A score of 0.50 and a score of 0.62 both land in Uncertain — there is deliberately no
single tipping point at 0.5.

---

## 3. Transparency label design (exact text)

Every label includes the band verdict, the AI-likelihood score, the confidence, the
per-signal breakdown, and an appeal pointer. Three variants, written out now:

**High-confidence AI** (combined ≥ 0.65, signals agree):
> ⚠️ **Likely AI-generated.** AI-likelihood **0.82** · confidence **0.86**.
> Both checks agreed: the writing rhythm was unusually uniform (burstiness 0.80) and the
> phrasing read as formulaic (LLM 0.83). This is an automated estimate, **not proof**. If
> you wrote this yourself, you can appeal below.

**High-confidence human** (combined ≤ 0.35, signals agree):
> ✅ **Likely human-written.** AI-likelihood **0.14** · confidence **0.88**.
> Both checks agreed: natural sentence-length variation (burstiness 0.12) and
> idiosyncratic phrasing (LLM 0.15). This is an automated estimate, **not a guarantee**
> of authorship.

**Uncertain** (0.35–0.65, or signals disagree, or single-signal, or too short):
> ❓ **Uncertain — inconclusive.** AI-likelihood **0.58** · confidence **0.41**.
> Our two checks disagreed (burstiness 0.20 vs LLM 0.90) / landed in the middle, so we
> can't make a reliable call. Treat this as **inconclusive** — do not use it as evidence
> either way.

---

## 4. Appeals workflow

- **Who can appeal:** anyone holding a `submission_id` — in practice the creator who
  submitted the text. No login in the prototype; the submission id is the access token.
- **What they provide:** `{ submission_id, reason, author? }`. `reason` is required.
- **What the system does on receipt:**
  1. Look up the submission. Unknown id → `404`.
  2. If already under review or resolved → return current status (idempotent), no
     duplicate.
  3. Otherwise create an appeal record `{ appeal_id, submission_id, reason, status:
     "under_review", created_at }` and flip the submission's `status` from `labeled` →
     `under_review`.
  4. Append an audit entry `appeal_opened` (appeal id, submission id, timestamp, reason).
  5. Return `{ appeal_id, submission_id, status, timestamp }`.
- **Human reviewer — the appeal queue** (`GET /appeals`): each row shows submission id,
  appeal id, the original label + AI-likelihood + confidence, **both signal scores**, the
  appellant's reason, text hash, status, and timestamps. The reviewer can resolve via
  `POST /appeal/<appeal_id>/resolve { decision: "upheld" | "overturned", note }`, which
  sets status to `resolved_upheld` / `resolved_overturned` and logs an `appeal_resolved`
  audit entry. An overturn records a corrected label but never deletes the original — the
  audit trail keeps both.

---

## 5. Anticipated edge cases (specific)

1. **Poetry / song lyrics with heavy repetition and short uniform lines.** Repeated
   refrains and consistently short lines drive sentence-length CV toward zero, so Signal 1
   scores it strongly AI even though it is human and creative. Mitigation: the
   disagreement override (the LLM judge often disagrees) pushes these to Uncertain rather
   than a false AI verdict.
2. **Non-native / ESL writing.** Simpler, more uniform sentence construction lowers CV
   *and* can read as "formulaic" to the LLM judge, so **both** signals can wrongly agree
   on AI — the highest-harm false positive. Mitigation: this is exactly why labels are
   probabilistic and appeals are frictionless; I also bias the threshold high (0.65) so
   the system is reluctant to flag a human.
3. **Very short text (a tweet, one sentence).** Variance is unestimable and the LLM judge
   is unreliable on short input. **Length gate:** the burstiness signal returns `null`
   for inputs under ~25 words or fewer than 2 sentences (variance needs at least two
   samples); that `null` triggers the single-signal / forced-Uncertain override rather
   than a guessed structural verdict.
4. **Mixed provenance** (human draft polished by AI, or AI draft heavily rewritten by a
   human). The binary human/AI framing genuinely can't represent this; the Uncertain band
   and the per-signal breakdown are the honest answer, not a forced call.

---

## Architecture

**Submission flow:** a creator `POST`s raw text to `/submit`; the rate limiter and a
length gate run first, then the text fans out to Signal 1 (burstiness, local) and Signal
2 (LLM fluency, Groq); the confidence scorer blends the two scores into a combined
AI-likelihood and a confidence value; the label builder maps those onto one of three
transparency labels; the full record (text **hash**, both signals, combined score, label,
timestamp) is appended to the audit log and returned to the client.
**Appeal flow:** the creator `POST`s the `submission_id` + reason to `/appeal`; the
system looks up the record, flips its status to `under_review`, writes an audit entry, and
returns the appeal id and new status for a human reviewer to action.

### Diagram

```
SUBMIT:
  client --text--> /submit --(rate limit + length gate)--> text
        text --> [Signal 1: burstiness] -----0..1----\
        text --> [Signal 2: LLM / Groq]  ----0..1----> [confidence scorer]
                                                            |
                                       combined score + confidence
                                                            v
                                                 [transparency label builder]
                                                            | label + explanation
                                                            v
                                                      [audit log] --record--> response

APPEAL:
  client --submission_id + reason--> /appeal --lookup--> [status: under_review]
                                            --status change--> [audit log] --> response
```

### API surface

| Method & path | Accepts | Returns |
|---|---|---|
| `POST /submit` | `{ text, author? }` | `{ id, signals:{ burstiness, llm_fluency }, combined_score, confidence, label, explanation, status, timestamp }` |
| `GET /result/<id>` | path `id` | stored result + current `status` |
| `POST /appeal` | `{ submission_id, reason, author? }` | `{ appeal_id, submission_id, status, timestamp }` |
| `GET /appeals` | — | appeal queue for human reviewers |
| `POST /appeal/<appeal_id>/resolve` | `{ decision, note }` | updated appeal record |
| `GET /audit` | optional `?submission_id=` | append-only audit entries |
| `GET /health` | — | `{ status: "ok" }` |

Conventions: scores are floats in `[0,1]` (1 = most AI-like); `label` ∈
`{likely_human, uncertain, likely_ai}`; errors return `{ error, detail }` with 400 /
404 / 429; the audit log stores a hash of the text, never the raw text; rate limiting
applies to `POST /submit` and `POST /appeal`.

---

## AI Tool Plan

Code-generation tool: **Claude (via Claude Code)**. The runtime LLM inside the app is
**Groq** (Signal 2). For each milestone I give Claude the named spec sections plus the
Architecture diagram, then verify the output myself before wiring it in.

### M3 — submission endpoint + first signal
- **Spec I provide:** §1 Detection signals (esp. Signal 1, the Groq LLM signal) + the
  Architecture diagram + the API surface row for `POST /submit`.
- **What I ask for:** a Flask app skeleton (`/submit`, `/log`, `/health`, error
  handling, the in-memory store + structured audit log) and the
  `llm_fluency(text) -> float | None` function (Groq call returning strict JSON,
  normalized to `[0,1]`, graceful failure → `None`).
- **How I verify:** call `llm_fluency()` directly on 4–5 strings (an evocative human
  paragraph, an obviously-AI paragraph, a one-liner) and confirm the scores move in the
  expected direction *before* wiring it into the endpoint. Then `curl /submit` and
  confirm the JSON shape (`content_id`, `attribution`, `confidence`, `label`) and a
  written audit entry visible via `GET /log`.

### M4 — second signal + confidence scoring
- **Spec I provide:** §1 (Signal 2, burstiness) + §2 Uncertainty representation + the
  diagram.
- **What I ask for:** the `burstiness(text) -> float` function (CV formula + `[0,1]`
  calibration + length gate) and the combiner (`combined_score`, `agreement`,
  `confidence`, the band logic, and the disagreement / single-signal / length-gate
  overrides).
- **What I check:** scores vary meaningfully between clearly-AI and clearly-human text;
  the disagreement override actually fires when I feed it split inputs; confidence drops
  on disagreement; the CV reference and band edges look calibrated (adjust if not).

### M5 — production layer (labels + appeals)
- **Spec I provide:** §3 Label variants + §4 Appeals workflow + the diagram.
- **What I ask for:** the label builder (maps band + scores → one of the three exact
  label texts with the signal breakdown filled in) and the `/appeal`, `/appeals`,
  `/appeal/<id>/resolve`, `/audit` endpoints with their status transitions and audit
  logging.
- **How I verify:** craft inputs that reach **all three** label variants (human,
  uncertain, AI); submit one, appeal it, and confirm status goes `labeled →
  under_review`, an `appeal_opened` audit entry is written, the appeal appears in
  `GET /appeals`, and a resolve call transitions status correctly.

---

## Open decisions to confirm during build
- Final CV reference (`0.60`) and band edges (`0.35` / `0.65`) after M4 calibration.
- Signal weights (`0.4` / `0.6`) — revisit if the LLM signal proves noisy.
- Audit-log persistence: in-memory dict for the prototype vs. a JSON file for surviving
  restarts.
