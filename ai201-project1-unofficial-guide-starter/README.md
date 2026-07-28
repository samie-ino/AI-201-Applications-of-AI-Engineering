# The Unofficial Guide — Project 1

A retrieval-augmented (RAG) assistant that answers practical first-year
questions for University of Oklahoma (Norman) students, grounded only in a
small corpus of student articles, reviews, and the official parking FAQ.

**Run it:**
```bash
pip install -r requirements.txt
cp .env.example .env            # paste your free Groq API key
python ingest.py                # inspect documents + chunks
python embed.py                 # build the ChromaDB index + retrieval test
python app.py                   # launch the Gradio chat UI (http://localhost:7860)
```

---

## Domain

A **campus survival guide for University of Oklahoma (Norman) students** —
navigating campus, study spots, meal plans, dorm choices, parking and transit,
and the unwritten tips that ease the freshman transition.

This knowledge is valuable because it is *experiential* rather than official:
OU's own pages publish policies and facts, not candid advice about which dorm
actually floods or where to study when Bizzell is packed during finals. That
advice instead sits scattered across student-newspaper columns, Quora threads,
and dorm-review sites. This system pulls those fragmented student voices into
one searchable, source-cited resource.

---

## Document Sources

Ten sources spanning four content shapes — long-form student-newspaper columns,
crowd-sourced Q&A, dorm reviews, and an official FAQ — so the corpus covers
different subtopics *and* different levels of reliability.

| # | Source | Type | URL or file path |
|---|--------|------|-----------------|
| 1 | OU Daily — "5 tips to survive your freshman year" | News column (opinion) | https://www.oudaily.com/culture/5-tips-to-survive-your-freshman-year-advice-from-an-ou-senior/article_dca7bdca-c29f-11e9-a6f0-bbe0b2f4741c.html |
| 2 | OU Daily — Campus Mini-guide | News (campus navigation) | https://www.oudaily.com/campus-mini-guide/article_dcf84c33-8fc3-5f6c-b282-b0051242ca3b.html |
| 3 | OU Daily — "Ten must-have apps for OU students" | News (listicle) | https://www.oudaily.com/news/ten-must-have-apps-for-ou-students/article_8b76ddb0-628d-11e7-bc1a-9bacddce66dc.html |
| 4 | OU Daily / The Covered Wagon — "Five tips to make your freshman transition easier" | **Satire / humor column** | https://www.oudaily.com/blogs/five-tips-to-make-your-freshman-transition-a-little-easier/article_18184fa2-265e-11e4-907d-0017a43b2370.html |
| 5 | OU Daily — "Best study spots around campus" | News column (opinion) | https://www.oudaily.com/l_and_a/arts_and_entertainment/column-best-study-spots-around-campus/article_f07ddb83-da64-5f57-bfa3-ea282f8ecf5d.html |
| 6 | OU Daily — "Six lesser-known places to study during finals" | News column (opinion) | https://www.oudaily.com/news/six-lesser-known-places-to-study-during-finals-week-at-ou/article_fca4ce4c-be65-11e6-a018-9fd929df7a20.html |
| 7 | OU Daily — "Don't eat a loss: how to plan your meal plan" | News column (opinion) | https://www.oudaily.com/l_and_a/don-t-eat-a-loss-how-to-plan-your-meal-plan/article_8b71a0da-2c98-11e4-a5ae-001a4bcf6878.html |
| 8 | Quora — "Tips and hacks for incoming OU freshmen" | Crowd-sourced Q&A | https://www.quora.com/What-are-some-tips-and-hacks-for-incoming-freshmen-at-the-University-of-Oklahoma |
| 9 | Roomsurf — Adams/Couch/Walker dorm reviews | User reviews (ratings + prose) | https://www.roomsurf.com/dorm-reviews/ou/adams,-couch,-and-walker-center/21369 |
| 10 | OU Parking & Transportation — FAQs & Policies | Official FAQ | https://www.ou.edu/parking/faqs-and-policies |

Each source is stored as a `.txt` file in `documents/` with a small metadata
header (`source`, `url`, `date`) above a `---` separator. **Source 4 is kept
deliberately** even though it is satire — it is labeled as such in its metadata
and serves as a real test of how the system handles an unreliable source (see
Failure Case Analysis).

---

## Chunking Strategy

Implemented in [`ingest.py`](ingest.py) (`chunk_text`).

**Chunk size:** target ~200 tokens, hard max **256 tokens**.

**Overlap:** ~40 tokens, applied *only* when a single section is too long and
must be split mid-topic — never between already-separate reviews or answers.

**Preprocessing before chunking:** documents were collected as clean `.txt`
(no live HTML scraping), so there are no tags, nav bars, or cookie banners to
strip. `load_documents` splits the metadata header from the body on the first
`---` line and parses `source`/`url`/`date` so that metadata can ride along with
every chunk. Body text is whitespace-trimmed; paragraphs are the primary split
unit.

**Approach — structure-aware recursive splitting, not a blind sliding window:**
1. Split each document on natural boundaries: paragraphs (`\n\n`), then
   sentences. Short headings (e.g. "4. Hang out at Suger's") are glued to the
   block they introduce so a chunk boundary can't orphan them.
2. Greedily group adjacent units up to the ~200-token target.
3. Only when a *single* unit exceeds the 256-token max is it split, with ~40
   tokens of overlap so a thought isn't severed mid-clause.
4. Merge any trailing fragment under ~30 tokens into its neighbor.

**Why this fits the documents:** the corpus has two shapes. Long-form OU Daily
columns and the parking FAQ spread one topic across several paragraphs — the
recursive split keeps a tip intact. Quora answers and Roomsurf reviews are
self-contained (one tip/review per entry) — splitting on boundaries *first*
means each short review stays its own chunk with no cross-bleed from overlap.
The **256-token ceiling is dictated by the embedding model** (`all-MiniLM-L6-v2`
truncates past 256 tokens), so any larger chunk would silently lose its tail
before embedding.

**Final chunk count:** **52 chunks** across 10 documents (token sizes: min 54,
max 212, mean ~155 — verified that no chunk exceeds the 256-token ceiling).

---

## Embedding Model

**Model used:** `all-MiniLM-L6-v2` via `sentence-transformers`. It runs locally
with no API key and no rate limits, and produces 384-dimension embeddings that
are strong for short-passage semantic similarity — a good fit for a corpus of
student tips and reviews. Its 256-token input ceiling is exactly what dictates
the 256-token hard max in the chunking strategy, so the two are consistent by
design. The vector store is a local ChromaDB `PersistentClient` at
`./chroma_data`, configured for **cosine** distance.

**Production tradeoff reflection:** If this were a real deployment and cost
weren't a constraint, I'd weigh:
- **Context length** — MiniLM truncates at 256 tokens, forcing small chunks. A
  model like OpenAI `text-embedding-3-large` or Voyage handles far longer
  inputs, so I could embed a whole dorm review or FAQ section without splitting
  and losing context across boundaries. This is the single biggest limitation
  here.
- **Domain accuracy** — a larger or domain-tuned model would better distinguish
  near-synonyms that matter in this corpus ("dorm" vs. "residential college").
- **Latency & hosting** — MiniLM is local and fast; an API-hosted model adds
  network latency and a per-call dependency but offloads compute.
- **Multilingual** — not needed for an English-only OU corpus, so I wouldn't
  pay for it here.

Net: MiniLM is the right *free, local* choice for this project; at scale I'd
move to a longer-context hosted model primarily to stop chunk-boundary
information loss.

---

## Grounded Generation

Implemented in [`generate.py`](generate.py) (`answer`). Generation uses Groq's
`llama-3.3-70b-versatile` at `temperature=0.2`.

**System prompt grounding instruction (verbatim, abridged):**
> "You answer using ONLY the numbered sources provided in the user's message.
> Base every claim strictly on the provided sources. Do not use outside
> knowledge, and do not guess. If the sources do not contain the answer, reply
> exactly: *'I don't know based on these sources.'* Cite the sources you used by
> their number, like [1] or [2][3]. … prefer the official source for facts
> (rules, prices, locations) and clearly frame student tips as opinion."

The grounding is enforced structurally, not just suggested:
- **Closed-book framing.** The user message contains a numbered "Sources:"
  block (the retrieved chunks) followed by the question. The model is told these
  are its *only* allowed knowledge.
- **Explicit refusal contract.** A fixed refusal string is mandated, so an
  out-of-domain question produces a clean "I don't know" rather than a plausible
  hallucination (verified — see Q-OOD below).
- **Weak-match filtering.** Before generation, chunks with cosine distance
  > 0.6 are dropped so a single noisy match can't pull the answer off-topic. If
  *nothing* survives the filter, the system refuses without even calling the LLM.

**How source attribution is surfaced:** attribution is **programmatically
guaranteed, not left to the model**. The LLM cites `[n]` inline, *and* after
generation `answer()` builds a deduplicated source list directly from the
retrieved chunks' metadata (`source`, `url`, `date`) and returns it in
`result["sources"]`; the Gradio UI renders this as a clickable "Sources" footer.
On a refusal the source list is cleared, so a non-answer is never falsely
attributed to unused chunks.

---

## Evaluation Report

All five questions were run through the full pipeline (`python generate.py`).
Responses below are the system's actual output, summarized.

| # | Question | Expected answer | System response (summarized) | Retrieval quality | Response accuracy |
|---|----------|-----------------|------------------------------|-------------------|-------------------|
| 1 | What study spots do students recommend, including quieter/lesser-known ones for finals? | At least one mainstream spot (Bizzell, Sarkeys, Beaird, Honors College) and one lesser-known finals spot | Named Beaird Lounge, couches in Richards Hall, the Nielsen Hall faculty lounge, and the Adams Tower 12th-floor lounge, cited [1][3][4] (Sources 5 & 6) | Relevant (top distance 0.22) | **Accurate** |
| 2 | How should a freshman manage meal points so they don't run out? | Pace/budget points; don't front-load spending | Said not to spend points all at once, favor cafe meals, and use meal exchanges; cited [1][2][3][4] and explicitly flagged the 2014 source as dated | Partially relevant | **Partially accurate** — correct on pacing but the meal-exchange detail leans on a 2014 article and is muddled |
| 3 | Which apps do OU students consider essential? | At least the OU App and Canvas access | Listed OU App, OU Innovate, SoonerSports2Go, Duolingo, GroupMe, Hooked, Pocket Points, Quizlet — all genuinely in Source 3 | Relevant (all chunks from Source 3) | **Accurate** |
| 4 | Where can students park for free near campus, and how do they get to main campus? | Lloyd Noble Center + CART shuttle | "Park for free on the north side of Lloyd Noble Center [1]; take the CART shuttle, every 5–10 min 7 a.m.–6 p.m." — cited the official FAQ | Relevant (top distance 0.33, correct chunk #1) | **Accurate** |
| 5 | What do students honestly say about the Adams/Couch/Walker towers? | Experiential tower-vs-residential-college tradeoffs | Gave the honest *mixed* picture: one positive review, several critical (maintenance, smell, peeling paint) recommending residential colleges instead | Relevant (all chunks from Source 9) | **Accurate** |
| OOD | "What is the OU football schedule this season?" (out-of-domain probe) | Should decline | "I don't know based on these sources." — no fabricated citation | n/a | **Accurate (correct refusal)** |

**Retrieval quality:** Relevant for 4 of 5 + the refusal; partially relevant for Q2.
**Response accuracy:** Accurate for 4 of 5; partially accurate for Q2.

---

## Failure Case Analysis

**Question that failed:** "What tips do students give for making the freshman
transition easier?"

**What the system returned:** A blend of genuine advice (attend class, get to
know your RA, get involved) *and* content from the satirical Covered Wagon
column — including "a satirical piece jokingly advises not walking in bike
lanes [1][4]." The satire article (Source 4) was the **#1 retrieval result, at
cosine distance 0.172 — the single strongest match in the entire corpus.**

**Root cause (tied to a specific pipeline stage):** This is a *retrieval* +
*corpus* failure, not a generation failure. The embedding model ranks Source 4
first because its title and body are a near-perfect semantic match for the
query ("freshman transition tips") — but **semantic similarity is completely
blind to source credibility.** The retriever has no signal that this source is a
joke; it only knows the text is on-topic. The only reason the model didn't
present "hang out at Suger's" or the dangerous "tip 5" as real advice is a
*manual* safeguard: I labeled Source 4 as satire in its metadata header and
added a `[NOTE: satire]` line in the body, which the grounding prompt's
"frame opinion vs. fact" rule picked up. Nothing in retrieval or the LLM
*detected* the satire — a query phrased to dodge that NOTE line could still
surface jokes as fact.

**What I would change to fix it:** (1) Add a per-source **reliability/credibility
field** to chunk metadata (`official` / `opinion` / `satire`) and either
down-weight or filter satire at retrieval time, or pass the reliability tag into
the prompt so the model must caveat it explicitly. (2) For a production system,
exclude satire from the indexed corpus entirely, or quarantine it behind an
explicit "show me the joke version" toggle. The deeper lesson: **a clean
retrieval score (0.172) is not the same as a trustworthy answer** — relevance
and reliability are different axes, and a pure vector search only measures the
first.

---

## Spec Reflection

**One way the spec helped me during implementation:** Writing the chunking and
retrieval sections of `planning.md` *before* coding forced the 256-token chunk
ceiling and the embedding model's 256-token input limit to be the *same number,
chosen for the same reason.* Because that constraint was written down explicitly
and tied to the model, the chunker and the embedder were consistent by
construction — `ingest.py` even asserts that no chunk exceeds 256 tokens. I
never hit the classic RAG bug where chunks are silently truncated at index time
because the splitter and the model disagreed on size.

**One way my implementation diverged from the spec, and why:** `planning.md`
configured ChromaDB with its default distance metric in mind, but during
Milestone 4 I switched the collection to **cosine** distance
(`hnsw:space="cosine"`). ChromaDB defaults to squared-L2, which on normalized
embeddings roughly doubles the distance numbers — good matches would have read
~0.45–0.66 and looked like weak retrievals against the "below 0.5" checkpoint
target. Cosine distance matched both the semantic-similarity framing in the plan
and the checkpoint's expected scale, so the divergence made the spec's own
success criteria measurable. (Separately, I chose Gradio's `ChatInterface` over
the two-box `Blocks` layout the assignment sketched, since the plan only
required "Gradio or Streamlit" and a chat box is self-explanatory in the demo.)

---

## AI Usage

**Instance 1 — implementing the chunker from the spec**
- *What I gave the AI:* The "Chunking Strategy" section of `planning.md` verbatim
  (target ~200 / max 256 tokens, ~40-token overlap only on over-long units,
  paragraph→sentence recursion, merge sub-30-token fragments) plus the metadata
  header format of the `.txt` files.
- *What it produced:* `ingest.py` with `load_documents()` and a structure-aware
  `chunk_text()` that counts tokens with the *same* MiniLM tokenizer the embedder
  uses, glues short headings to their following block, and only adds overlap as a
  last resort.
- *What I changed or overrode:* I directed it to verify the output rather than
  trust it — running the inspection report surfaced that the corpus produced
  exactly **52 chunks**, just above the assignment's 50-chunk floor, and confirmed
  zero chunks over the 256 ceiling. I kept the count rather than shrinking chunks,
  since the token-size distribution (mean ~155) was healthy.

**Instance 2 — embedding/retrieval and the distance-metric fix**
- *What I gave the AI:* The "Retrieval Approach" section plus `chroma_example.py`
  as a reference, asking for `build_index()` (embed all chunks, upsert with
  source metadata) and `retrieve(query, k=4)`.
- *What it produced:* `embed.py` using a local `PersistentClient`, storing
  `source`/`url`/`date`/`filename`/`chunk_index` metadata, and a retrieval
  function returning chunks with distances.
- *What I changed or overrode:* The first version used ChromaDB's default
  squared-L2 distance, which made my good matches *look* weak (~0.6) against the
  "below 0.5" checkpoint. I had it switch the collection to **cosine** distance
  and normalize the embeddings, after which the same queries scored 0.17–0.34. I
  also had it delete-and-rebuild the collection on each run so an edited chunker
  never leaves stale vectors behind.
