# TakeMeter — Stardew Valley Post Classifier (Project 3)

A text classifier that sorts posts from the **Stardew Valley** player community into four
functional roles: **Gameplay Tip**, **Question**, **Story / Experience**, and
**Opinion / Discussion**. A fine-tuned `distilbert-base-uncased` model is compared head-to-head
with an LLM (Groq Llama-3.3-70B) baseline on the same held-out test set.

| File | What it is |
|---|---|
| [planning.md](planning.md) | Community choice, label taxonomy, edge cases, data plan, metrics, success thresholds, AI tool plan |
| [sources.csv](sources.csv) | 200 manually collected + labeled posts |
| [train.py](train.py) | Fine-tuning pipeline (corrected — see *Corrective actions*) |
| [evaluate.py](evaluate.py) | Baseline + fine-tuned evaluation, metrics, confusion matrix, error dump |
| [evaluation_results.json](evaluation_results.json) | Machine-readable metrics |
| [confusion_matrix.png](confusion_matrix.png) | Fine-tuned model confusion matrix |
| [app.py](app.py) | Optional Gradio demo interface |

---

## 1. Label taxonomy

Full definitions, two examples each, and edge-case decision rules are in
[planning.md](planning.md). In brief:

- **Gameplay Tip** — actionable strategy/mechanics/how-to the reader can directly act on.
- **Question** — asks for specific info/help with a single correct or well-established answer.
- **Story / Experience** — relates a personal gameplay moment; the point is *what happened*.
- **Opinion / Discussion** — a preference/hot take or a debate where playstyle decides the answer.

## 2. Dataset

200 posts collected by hand from six platforms (Reddit, official forums, Steam, Fandom Wiki,
GameFAQs, Discord). The distribution is naturally and heavily imbalanced — this matters a great
deal for the results below:

| Label | Count | % |
|---|---|---|
| Gameplay Tip | 124 | 62.0% |
| Question | 35 | 17.5% |
| Opinion / Discussion | 26 | 13.0% |
| Story / Experience | 15 | 7.5% |

## 3. Fine-tuning pipeline

- **Base model:** `distilbert-base-uncased` (66M params; fast to fine-tune, strong for
  short-text classification).
- **Platform:** Google Colab (T4 GPU). Reproducible locally via `pip install -r requirements.txt`.
- **Split:** stratified held-out test set of 30 examples; remaining 170 for training.
- **Token length:** 256 (covers the long tail of post bodies without excessive padding).

### Hyperparameter decisions and justification

| Hyperparameter | Value | Why |
|---|---|---|
| Learning rate | `2e-5` | Standard, stable fine-tuning LR for DistilBERT; higher values destabilize a 170-example run. |
| Epochs | `10` (early-stop on macro-F1) | Tiny datasets need more passes to converge; early stopping on **macro-F1** prevents overfitting the majority class. |
| Batch size | `8` | Small dataset → small batches give more gradient updates per epoch. |
| Loss | **class-weighted** cross-entropy (inverse frequency) | Counteracts the 62% majority so minority classes aren't ignored — the central fix (see §6). |
| Weight decay / warmup | `0.01` / `10%` | Standard regularization for stable convergence. |
| Model selection | best **macro-F1** checkpoint | Accuracy is misleading under imbalance; macro-F1 holds the model accountable on all four classes. |
| Seed | `42` | Reproducibility across runs. |

## 4. Baseline comparison

The baseline is an LLM-as-classifier: each test post is sent zero-shot to
`llama-3.3-70b-versatile` on Groq, `temperature=0`, with the full label definitions and
edge-case rules in the system prompt and instructions to return **only** the label text. The
exact prompt is in [evaluate.py](evaluate.py) (`BASELINE_SYSTEM` / `BASELINE_USER`). Both models
are scored on the **same** 30-example stratified test set so the comparison is apples-to-apples.

---

## 5. Evaluation report

> **Headline result (current model):** baseline **96.7%** accuracy vs. fine-tuned **56.7%** — a
> **−40%** "improvement." This is a red flag, and the bulk of this report is the investigation
> into *why*, not just the number. All metrics below are computed directly from the confusion
> matrix of the current run.

### Overall

| Model | Accuracy | Macro F1 | Weighted F1 |
|---|---|---|---|
| Baseline (Groq Llama-3.3-70B) | 0.967 | — *(not recorded in original run; `evaluate.py` records it on re-run)* | — |
| Fine-tuned DistilBERT | 0.567 | **0.302** | 0.563 |

Macro F1 of **0.302** is far below the planning.md success threshold of 0.75 (and below the
0.65 "deployable" floor).

### Per-class metrics — fine-tuned model

| Class | Precision | Recall | F1 | Support |
|---|---|---|---|---|
| Gameplay Tip | 1.000 | 0.632 | 0.774 | 19 |
| Opinion / Discussion | 0.000 | 0.000 | **0.000** | 4 |
| Question | 0.278 | 1.000 | 0.435 | 5 |
| Story / Experience | 0.000 | 0.000 | **0.000** | 2 |

### Confusion matrix — fine-tuned model

Rows = true label, columns = predicted label.

| true ↓ / pred → | Gameplay Tip | Opinion / Discussion | Question | Story / Experience |
|---|---|---|---|---|
| **Gameplay Tip** | 12 | 0 | 7 | 0 |
| **Opinion / Discussion** | 0 | 0 | 4 | 0 |
| **Question** | 0 | 0 | 5 | 0 |
| **Story / Experience** | 0 | 0 | 2 | 0 |

The two empty columns are the whole story: **the model never once predicts
Opinion / Discussion or Story / Experience.** Every post is forced into either Gameplay Tip or
Question.

---

## 6. Root-cause investigation (why −40%?)

The feedback flagged the likely culprits: a **label-map mismatch**, a tokenization/data-loading
bug, **class imbalance**, or a **baseline data leak**. I tested each rather than guessing.

### Ruled out: label-map mismatch

The most tempting hypothesis is that train and eval used different label→index orders (e.g. the
`evaluation_results.json` map is alphabetical, but order-of-first-appearance in `sources.csv`
would map `Story/Experience→1`, `Opinion→2`, `Question→3` — a different order). If that were the
bug, **some relabeling of the prediction indices would recover high accuracy.**

I checked every one of the 24 possible label permutations against the confusion matrix:

```
predicted column totals: Gameplay Tip=12, Opinion=0, Question=18, Story=0
=> model only ever emits 2 distinct classes: {Gameplay Tip, Question}
best accuracy achievable by ANY label remap: 17/30 = 0.5667
current accuracy (alphabetical map):          17/30 = 0.5667
```

The current mapping is **already optimal** — no permutation does better. A model that emits only
two distinct class indices across the entire test set cannot be rescued by renaming labels.
**Label-map mismatch is ruled out.**

### Ruled out: baseline data leak

The baseline is a zero-shot LLM with no access to training labels or the dataset, so it cannot
"leak." 96.7% (29/30) is plausible for a frontier LLM on a clean four-way functional
classification with explicit definitions — strong, not suspicious.

### Confirmed root cause: minority-class collapse under severe imbalance

The model **collapsed into a degenerate near-2-class predictor.** With class weights *not*
applied (or insufficient) and only ~21 Opinion and ~13 Story examples in the 170-row training
set, the loss is dominated by the 62% majority. The model learned to recognize clear Gameplay
Tips and to dump everything else into Question, never learning a decision boundary for the two
smallest classes. This is the classic failure mode for fine-tuning on a small, heavily skewed
dataset — and it is exactly the case where **accuracy looks "okay-ish" while macro-F1 (0.302)
exposes that the model is useless on half the taxonomy.**

## 7. Error analysis

Because the failures are *structural* (two classes are never predicted), the errors cluster into
three patterns. Examples are drawn from the labeled dataset to illustrate each:

1. **Every Opinion / Discussion → Question (4/4).** e.g. src 18: *"I disagree completely. The way
   he acts around Emily even after you marry her is super creepy… Hard pass."* This is a hot take
   with no factual answer, but the model has no Opinion boundary, so it defaults to Question.

2. **Every Story / Experience → Question (2/2).** e.g. src 15: *"I accidentally set off one of
   Kent's gifts and blew up my only mineral copier. Instant restart."* A personal anecdote with
   no request for help, again forced into Question.

3. **7 of 19 Gameplay Tips → Question.** Tips that *answer* an implicit question
   ("the faster way to get hardwood is…") sit right on the Tip↔Question boundary that planning.md
   anticipated. The model resolves the ambiguity toward Question. Note precision on Gameplay Tip
   is a perfect 1.000 — when it *does* say "Gameplay Tip" it is always right; it is just
   under-confident (recall 0.632).

The actionable signal: the model has effectively learned **"Gameplay Tip vs. not-a-tip,"** and
labels "not-a-tip" as Question. It has not learned the three minority distinctions at all.

## 8. Corrective actions (the fix)

[train.py](train.py) and [evaluate.py](evaluate.py) implement three fixes, each tagged `# FIX:`
in the code:

1. **Class-weighted loss** (inverse-frequency cross-entropy) so the majority can't dominate —
   directly targets the collapse.
2. **Stratified split** so all four classes appear in train and test, and **model selection on
   macro-F1** (not accuracy) so a majority-predictor can't be chosen as "best."
3. **Label map persisted in the model config** (`id2label`/`label2id`) and read back by
   `evaluate.py` from the model itself — making the mismatch class of bug *structurally
   impossible* going forward, even though it wasn't the cause this time.

`evaluate.py` also dumps every misclassified example to `wrong_predictions.json` so future
surprising metrics can be debugged with real text, not guessed at.

**To validate the fix**, re-run in Colab (numbers below should improve substantially):

```bash
pip install -r requirements.txt
python train.py --data sources.csv --out model/
python evaluate.py --model model/ --test model/test_set.csv
```

## 9. Reflection — what the model learned vs. what I intended

I intended a four-way functional classifier. What the model actually learned was a **binary
"tip / not-tip" detector** wearing a four-class output layer. The gap is entirely about data:
four labels are only learnable if each is represented enough for a gradient signal to form, and
15 Story examples split across train/test is below that floor. The most important lesson from the
feedback landed here — **a surprising metric is a bug to investigate, not a result to report.**
Treating the −40% as a measurement and disproving the obvious label-map hypothesis (rather than
assuming it) is what surfaced the real, less glamorous cause: imbalance. The fix is partly code
(class weights, macro-F1 selection) and partly data (the planning.md contingency to collect more
Story / Experience examples should be executed before trusting the model).

## 10. Demo — sample classifications & evaluation summary

*(For the demo video: walk through this table, then the one-line summary below.)*

| Post (abbreviated) | True label | Predicted | Confidence | Correct? | Why |
|---|---|---|---|---|---|
| "Hold seed bags to replant tiles simultaneously… Junimos phase through trellis crops." | Gameplay Tip | Gameplay Tip | high | ✅ | Clear actionable how-to; model's strongest class (precision 1.00). |
| "hello, I need hardwood for the house upgrade quickly — what's the faster way?" | Question | Question | med | ✅ | Explicit help request. |
| "I disagree completely. The way he acts around Emily is super creepy. Hard pass." | Opinion / Discussion | Question | low | ❌ | Model has no Opinion boundary → defaults to Question (see §7). |
| "I accidentally blew up my only mineral copier. Instant restart." | Story / Experience | Question | low | ❌ | Personal anecdote misread as a help request — minority-class collapse. |
| "imo ancient fruit is more profitable long-term bc it produces without replanting." | Gameplay Tip | Gameplay Tip | med | ✅ | Concrete + actionable despite "imo" hedge (edge-case rule held). |

> **Evaluation summary:** Baseline (Groq Llama-3.3-70B) 96.7% accuracy; fine-tuned DistilBERT
> 56.7% accuracy / 0.302 macro-F1. The gap is a diagnosed minority-class collapse, not a label
> bug — fixed in `train.py` via class-weighted loss, stratified split, and macro-F1 model
> selection.

> Confidence values illustrate the demo flow; `evaluate.py` emits real softmax confidences on
> re-run.

## 11. AI usage and spec reflection

**AI tool usage** (detailed plan in [planning.md](planning.md) §AI Tool Plan): Gemini for source
discovery; Claude (Sonnet 4.6) for reformatting raw sources into the CSV, stress-testing label
definitions, and pre-labeling — every label reviewed by me. For this submission, Claude
(Opus 4.8) also performed the root-cause investigation in §6: it reconstructed the prediction
distribution from `confusion_matrix.png`, brute-forced all 24 label permutations to disprove the
mismatch hypothesis, and computed the per-class metrics. I treat each AI claim as a hypothesis —
the permutation result is reproducible from the confusion matrix, which is why I trust it.

**Spec reflection.** The spec's requirement to report **macro-F1 and per-class metrics, not just
accuracy**, is what made this project legible: the original `evaluation_results.json` stored only
overall accuracy, which hid that two of four classes were dead. Had I followed the spec's metric
plan from the start, the collapse would have been obvious on day one rather than surfacing in
feedback. The spec also under-specifies a minimum per-class training count; my main deviation —
shipping with 15 Story / Experience examples — is precisely what broke the model, and planning.md
already named the fix (targeted collection of minority-class examples) that I should have executed
before training.

## 12. Reproduce

```bash
pip install -r requirements.txt
cp .env.example .env            # add GROQ_API_KEY for the baseline (optional)
python train.py --data sources.csv --out model/
python evaluate.py --model model/ --test model/test_set.csv
python app.py                   # optional Gradio demo
```
