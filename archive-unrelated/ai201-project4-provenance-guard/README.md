# Provenance Guard — AI-Text Provenance Detector (Project 4)

Provenance Guard accepts a piece of text, runs it through **two independent detection
signals**, blends them into a single **calibrated confidence score**, and returns a
**transparency label** that is always probabilistic, always shows its work, and is always
contestable through an **appeals workflow**. The whole pipeline is fronted by rate
limiting and backed by a structured, append-only audit log.

Stack: **Flask** + **Flask-Limiter** + **Groq** (Llama-3.3-70B for the LLM signal).

| File | What it is |
|---|---|
| [planning.md](planning.md) | The spec: architecture, the two signals + blind spots, uncertainty model, label variants, appeals workflow, edge cases, AI tool plan |
| [app.py](app.py) | Flask app — `/submit`, `/appeal`, `/appeals`, `/appeal/<id>/resolve`, `/log`, `/health` |
| [detector.py](detector.py) | Both signals, the confidence combiner, and the transparency-label builder |
| [store.py](store.py) | JSON-file-backed audit log, submissions, and appeals |
| [requirements.txt](requirements.txt) | Dependencies |

---

## 1. Architecture

**Submission flow.** A creator `POST`s raw text to `/submit`. The rate limiter and a
length gate run first, then the text fans out to **Signal 1** (LLM fluency, Groq) and
**Signal 2** (burstiness, local). The confidence combiner blends the two scores into a
combined AI-likelihood and a confidence value; the label builder maps those onto one of
three transparency labels; the full record (text **hash**, both signals, combined score,
label, timestamp) is appended to the audit log and returned.

**Appeal flow.** The creator `POST`s the `content_id` + `creator_reasoning` to `/appeal`;
the system looks up the record, flips its status to `under_review`, writes an audit entry
capturing the appeal alongside the original decision, and returns a confirmation. A human
reviewer sees the queue at `GET /appeals` and resolves via `POST /appeal/<id>/resolve`.

```
SUBMIT:
  client --text--> /submit --(rate limit + length gate)--> text
        text --> [Signal 1: LLM / Groq]  ----0..1----\
        text --> [Signal 2: burstiness]  ----0..1----> [confidence combiner]
                                                            |
                                       combined score + confidence
                                                            v
                                                 [transparency label builder]
                                                            | label + explanation
                                                            v
                                                      [audit log] --record--> response

APPEAL:
  client --content_id + creator_reasoning--> /appeal --lookup--> [status: under_review]
                                            --status change--> [audit log] --> response
```

### API reference

| Method & path | Accepts | Returns |
|---|---|---|
| `POST /submit` | `{ text, creator_id }` | `content_id`, `attribution`, `confidence`, `combined_score`, `label`, `signals{llm_fluency,burstiness}` |
| `POST /appeal` | `{ content_id, creator_reasoning }` | `appeal_id`, `status: under_review` |
| `GET /appeals` | — | reviewer queue (appeals + snapshot of original decision) |
| `POST /appeal/<appeal_id>/resolve` | `{ decision: upheld\|overturned, note }` | updated appeal status |
| `GET /log` | `?limit=` | recent structured audit entries |
| `GET /health` | — | `{ status: "ok" }` |

---

## 2. Detection signals — and *why* these two

I deliberately paired one **cheap, deterministic, structural** signal with one **richer,
semantic** signal so they fail in *different* ways. Two detectors that share a failure
mode give false confidence; two that fail independently let their **disagreement** become
information (see §3).

### Signal 1 — LLM fluency / perplexity (Groq)
- **What it measures:** how formulaic and low-surprise the phrasing is — even tone,
  hedging, formulaic transitions ("Moreover,", "In conclusion,"), absence of personal
  voice. Groq returns `{"ai_likelihood": 0-100}`, normalized to `s1 ∈ [0,1]`.
- **Why it separates human vs AI:** AI decodes high-probability tokens → unusually smooth,
  low-perplexity prose. Humans make more surprising, idiosyncratic word choices.
- **Why it's the first signal:** it produces a usable score even on short text, which the
  structural signal cannot (variance needs ≥2 sentences).
- **Blind spot:** a fluent or AI-edited *human* text reads smoothly and gets flagged; the
  judge is itself probabilistic and can be confidently wrong.

### Signal 2 — Burstiness (sentence-length variation, local)
- **What it measures:** the coefficient of variation of sentence lengths,
  `CV = stdev/mean`, mapped `s2 = clamp(1 − CV/0.60, 0, 1)`. Low variation → AI-like.
- **Why it separates human vs AI:** humans are "bursty" (short punchy sentence next to a
  long winding one); LLMs tend to even, uniform pacing.
- **Blind spot:** blind to meaning and register. Formal/templated human writing and
  non-native English have uniform sentence lengths → wrongly flagged AI (see §7).

### Combining them
```
combined_score = 0.6 * s1 + 0.4 * s2      # LLM weighted higher (richer signal)
agreement      = 1 − |s1 − s2|
```
The LLM gets the higher weight because it reasons about meaning; burstiness is a blunt
structural proxy that is easy to fool. Weights, the CV reference (0.60), and the band
edges are all declared in [planning.md](planning.md) §1–§2 so the implementation has
concrete targets rather than magic numbers.

---

## 3. Confidence scoring — why this approach

A single AI-likelihood number isn't enough: a 0.6 from two *agreeing* signals means
something very different from a 0.6 produced by one signal screaming "AI" and the other
"human." So **confidence is separate from the AI-likelihood score** and is driven by two
things — distance from the 0.5 coin-flip *and* how much the two signals agree:

```
confidence = clamp( (|combined − 0.5| * 2) * (0.5 + 0.5 * agreement), 0, 1 )
```

Three bands (not a binary flip at 0.5):

| combined_score | band |
|---|---|
| `< 0.35` | Likely human |
| `0.35 – 0.65` | Uncertain |
| `> 0.65` | Likely AI |

Plus a **forced-Uncertain override** when `|s1 − s2| > 0.40` (signals strongly disagree),
either signal is `null`, or the text is too short. This override is the whole point of
running two signals: if they contradict each other, the honest answer is "we don't know,"
not the average.

### Two real submissions with noticeably different confidence (from M4 testing)

**High confidence — clearly human:**
> `"ok so i finally tried that new ramen place downtown and honestly? underwhelming…"`
> `s1 (LLM) = 0.20`, `s2 (burstiness) = 0.00`, **combined = 0.12**, **confidence = 0.68** → **Likely human**

**Low confidence — an AI text the signals disagreed on:**
> `"Artificial intelligence represents a transformative paradigm shift in modern society…"`
> `s1 (LLM) = 0.90`, `s2 (burstiness) = 0.37`, **combined = 0.69**, **confidence = 0.28** → **Uncertain (forced)**

The second case is the design working: the LLM caught the formulaic *phrasing*, but this
AI sample happens to vary its *sentence lengths*, so burstiness read it as human-ish. The
disagreement (|Δ| = 0.53) collapses confidence from 0.68 to 0.28 and forces Uncertain —
even though the raw combined score (0.69) sits in the "Likely AI" band. A constant scorer
could never produce this spread; these numbers show the scoring varies meaningfully.

**If I were deploying this for real:** I'd calibrate the CV reference and band edges
against a labeled corpus (they're currently reasoned defaults), bias the AI threshold even
higher to further reduce false accusations of humans, and add a third cheap signal
(e.g. token-level perplexity from a small local model) so a single flaky signal can't swing
the verdict.

---

## 4. Transparency label — all three variants

Every label states the band, the AI-likelihood, the confidence, the per-signal
breakdown, and a caveat. It is **never** a bare verdict, and the text changes with the
score. Exact rendered output from live runs:

**Likely AI (high combined score, signals agree):**
> ⚠️ **Likely AI-generated.** AI-likelihood 0.77 · confidence 0.45. Both checks leaned AI:
> the writing rhythm was relatively uniform (burstiness 0.57) and the phrasing read as
> formulaic (LLM 0.90). This is an automated estimate, **not proof**. If you wrote this
> yourself, you can appeal.

**Likely human (low combined score, signals agree):**
> ✅ **Likely human-written.** AI-likelihood 0.12 · confidence 0.68. Both checks leaned
> human: natural sentence-length variation (burstiness 0.00) and idiosyncratic phrasing
> (LLM 0.20). This is an automated estimate, **not a guarantee** of authorship.

**Uncertain (mid-range, or signals disagree, or single-signal, or too short):**
> ❓ **Uncertain — inconclusive.** AI-likelihood 0.40 · confidence 0.19. We can't make a
> reliable call because both checks landed in the middle. Treat this as **inconclusive** —
> do not use it as evidence either way.

The Uncertain variant adapts its *reason* clause to the override that fired — "our two
checks disagreed (burstiness X vs LLM Y)", "only one check was available (…)", or "both
checks landed in the middle" — so the user learns *why* it's inconclusive.

---

## 5. Appeals workflow

Anyone holding a `content_id` (the creator) can appeal by sending `content_id` +
`creator_reasoning`. On receipt the system: (1) looks up the submission (404 if unknown),
(2) creates an appeal with a **snapshot of the original decision**, (3) flips the
submission's status to `under_review` and marks it `appealed`, and (4) writes an
`appeal_opened` audit entry. A reviewer reads `GET /appeals` and resolves with
`upheld`/`overturned`; an overturn marks the submission `human_corrected` but never
deletes the original — the audit trail keeps both.

Live example (a non-native English speaker contesting the §7 false positive):

```
POST /appeal  { content_id: a52a235e…, creator_reasoning: "I wrote this myself…
                I am a non-native English speaker and my writing style may appear
                more formal than typical." }
=> { appeal_id: b86bad06…, status: "under_review" }
```

---

## 6. Rate limiting

Configured with Flask-Limiter (`storage_uri="memory://"`) on `/submit` and `/appeal`:

```python
@limiter.limit("10 per minute;100 per day")
```

**Reasoning (defensible, not arbitrary):** a real creator checks their own drafts
occasionally and may iterate a few times in a sitting — **10/minute** comfortably covers
that while stopping a script from hammering the (paid, latency-bound) Groq call. **100/day**
is a soft daily ceiling: far above any honest single user, low enough that an abusive
client is throttled before running up a large bill.

**Evidence** — 12 rapid requests against the 10/min limit:
```
200 200 200 200 200 200 200 200 200 200 429 429
```
The first 10 succeed; the 11th and 12th return **429 Too Many Requests**.

---

## 7. Known limitations

**Formal / academic human writing and non-native (ESL) English are the worst case, and it
is structural, not a data problem.** Both signals key on properties that this exact kind of
writing shares with AI:
- **Burstiness** measures sentence-length *uniformity*. Careful, formal writers — and many
  ESL writers — produce evenly-sized sentences, so CV is low and Signal 2 reports "AI."
- **The LLM judge** keys on smooth, low-surprise, formulaic phrasing. Polished formal prose
  *is* smooth and formulaic, so Signal 1 also reports "AI."

Because both signals fail the *same way* here, they agree, the disagreement override does
**not** fire, and the system emits a high-confidence "Likely AI" — a false accusation of a
real human. This is exactly what happened to the monetary-policy paragraph in §4 (combined
0.77). It's the reason the label is always probabilistic and the appeals flow exists.

A second, opposite limitation: **AI text with deliberately varied sentence structure**
evades burstiness (the §3 AI sample scored burstiness 0.37, i.e. "human-ish"), which is why
that case correctly degraded to Uncertain rather than a false "human" verdict.

---

## 8. Complete audit log

Every event is a structured JSON entry (`store.py` → `audit_log.json`), never `print()`.
Classification entries carry the timestamp, content ID, attribution, confidence, **both
individual signal scores**, the combined score, and `appeal_filed`; appeal entries carry
`status: under_review` and the `appeal_reasoning`. Sample:

```json
{
  "event": "classified",
  "content_id": "a52a235e-4e38-46f0-98c2-3a2f7922e555",
  "creator_id": "u-formal",
  "timestamp": "2026-07-02T05:24:12.000Z",
  "attribution": "likely_ai",
  "confidence": 0.451,
  "combined_score": 0.769,
  "llm_score": 0.9,
  "burstiness_score": 0.574,
  "status": "classified",
  "appeal_filed": false
}
{
  "event": "appeal_opened",
  "content_id": "a52a235e-4e38-46f0-98c2-3a2f7922e555",
  "appeal_id": "b86bad06-e0d6-4d8c-b8ab-19faea7f0405",
  "timestamp": "2026-07-02T05:24:26.471Z",
  "attribution": "likely_ai",
  "confidence": 0.451,
  "llm_score": 0.9,
  "burstiness_score": 0.574,
  "status": "under_review",
  "appeal_filed": true,
  "appeal_reasoning": "I wrote this myself from personal experience. I am a non-native English speaker…"
}
```

---

## 9. Spec reflection

**One way the spec guided the build.** Writing the three label variants and the exact
band thresholds *before* any code (planning.md §2–§3) meant `combine()` and `build_label()`
had concrete targets. When I generated the combiner, I could check it line-by-line against
the spec (bands 0.35/0.65, weights 0.6/0.4, disagreement 0.40, single-signal confidence cap
0.5) and catch any silent drift — rather than eyeballing whether "reasonable-looking"
scoring matched my intent. Declaring up front that *disagreement lowers confidence* is what
made the tricky "clearly-AI-but-bursty" case (§3) resolve sensibly instead of surprising me.

**One way the implementation diverged.** The spec's original **length gate** was "under ~40
words or fewer than 3 sentences." In practice, variance only needs *two* samples, and one of
the required test inputs (a formal 2-sentence paragraph) is precisely the case burstiness
*should* score — so a 3-sentence floor would have thrown away a signal I wanted. I lowered
the gate to "under ~25 words or fewer than 2 sentences" and updated planning.md §5 to match.
(Relatedly, I swapped the signal *numbering* — LLM became Signal 1 — because the M3 demo text
was too short for burstiness to score reliably.)

---

## 10. AI usage

I used Claude (via Claude Code) as the code-generation tool against the planning.md spec;
Groq (Llama-3.3-70B) is the runtime LLM inside Signal 1.

1. **Signal 2 + the combiner.** I directed the AI to generate the `burstiness()` function
   (CV formula + `[0,1]` calibration) and the confidence combiner from planning.md §1–§2.
   It produced working code, but I **overrode the length gate** (it had followed the spec's
   3-sentence floor, which nulled out the 2-sentence formal test case) and **verified every
   threshold** against the spec before wiring it in. Testing the four required inputs
   surfaced the "clearly-AI → Uncertain" disagreement case, which I kept as correct behavior
   rather than "fixing."

2. **The label builder + `/appeal` endpoint.** I directed the AI to generate the three-way
   `build_label()` and the appeal endpoint from planning.md §3–§4. I **revised the field
   names** to `content_id` / `creator_reasoning` (the spec had used `submission_id` /
   `reason`) so the endpoint matched the tested contract, and I **added adaptive reasoning**
   to the Uncertain label so it explains *why* it's inconclusive (disagreement vs.
   single-signal vs. mid-range) instead of showing static text. I confirmed all three
   variants were reachable and that an appeal actually flips status and logs before
   considering it done.

A recurring rule: I treat generated code as a draft to verify against the spec and real
runs, not as a finished answer — every number in §3–§8 is copied from an actual execution.

---

## 11. Reproduce

```bash
pip install -r requirements.txt
cp .env .env            # ensure GROQ_API_KEY is set
python app.py           # serves on http://localhost:5000  (use_reloader=False)

# classify
curl -s -X POST http://localhost:5000/submit -H "Content-Type: application/json" \
  -d '{"text": "…", "creator_id": "me"}' | python -m json.tool

# appeal (use a content_id from a /submit response)
curl -s -X POST http://localhost:5000/appeal -H "Content-Type: application/json" \
  -d '{"content_id": "…", "creator_reasoning": "I wrote this myself."}' | python -m json.tool

# audit log
curl -s http://localhost:5000/log | python -m json.tool
```

Runtime data (`audit_log.json`, `submissions.json`, `appeals.json`) is generated on first
use and is gitignored.
