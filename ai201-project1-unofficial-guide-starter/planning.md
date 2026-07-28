# Project 1 Planning: The Unofficial Guide

> Write this document before you write any pipeline code.
> Your spec and architecture diagram are what you'll use to direct AI tools (Claude, Copilot, etc.) to generate your implementation — the more specific they are, the more useful the generated code will be.
> Update the Retrieval Approach and Chunking Strategy sections if you change your approach during implementation.
> Update this file before starting any stretch features.



---

## Domain

<!-- What domain did you choose? Why is this knowledge valuable and hard to find through official channels? -->

**Campus survival guide for University of Oklahoma (Norman) students.**

This Unofficial Guide covers practical first-year survival knowledge for University of Oklahoma (Norman) students — navigating campus, study spots, meal plans, dorm choices, parking and transit, and the unwritten tips that ease the freshman transition. This knowledge is hard to find officially because OU's own pages publish policies and facts, not candid experiential advice, which instead sits scattered across student-newspaper columns, Reddit threads, and dorm-review sites. This guide pulls those fragmented student voices into one searchable resource.

---

## Documents

<!-- List your specific sources: URLs, subreddit names, forum threads, or file descriptions.
     Aim for at least 10 sources that together cover different subtopics or perspectives within your domain. -->

| # | Source | Description | URL or location |
|---|--------|-------------|-----------------|
| 1 | OU Daily — "5 tips to survive your freshman year" | Senior's advice: attend class, meal points, roommates | https://www.oudaily.com/culture/5-tips-to-survive-your-freshman-year-advice-from-an-ou-senior/article_dca7bdca-c29f-11e9-a6f0-bbe0b2f4741c.html |
| 2 | OU Daily — Campus Mini-guide | Navigating North vs. South Oval, key buildings | https://www.oudaily.com/campus-mini-guide/article_dcf84c33-8fc3-5f6c-b282-b0051242ca3b.html |
| 3 | OU Daily — "Ten must-have apps for OU students" | OU app, Canvas, campus maps, transit apps | https://www.oudaily.com/news/ten-must-have-apps-for-ou-students/article_8b76ddb0-628d-11e7-bc1a-9bacddce66dc.html |
| 4 | OU Daily — "Five tips to make your freshman transition easier" | Adjustment and social advice | https://www.oudaily.com/blogs/five-tips-to-make-your-freshman-transition-a-little-easier/article_18184fa2-265e-11e4-907d-0017a43b2370.html |
| 5 | OU Daily — "Best study spots around campus" | Bizzell library, Sarkeys, Beaird lounge, Honors College | https://www.oudaily.com/l_and_a/arts_and_entertainment/column-best-study-spots-around-campus/article_f07ddb83-da64-5f57-bfa3-ea282f8ecf5d.html |
| 6 | OU Daily — "Six lesser-known places to study during finals" | Hidden and quiet study spots | https://www.oudaily.com/news/six-lesser-known-places-to-study-during-finals-week-at-ou/article_fca4ce4c-be65-11e6-a018-9fd929df7a20.html |
| 7 | OU Daily — "How to plan your meal plan" | Meal points strategy, not overspending | https://www.oudaily.com/l_and_a/don-t-eat-a-loss-how-to-plan-your-meal-plan/article_8b71a0da-2c98-11e4-a5ae-001a4bcf6878.html |
| 8 | Quora — "Tips and hacks for incoming OU freshmen" | Crowd-sourced student tips (RAs, dorm life) | https://www.quora.com/What-are-some-tips-and-hacks-for-incoming-freshmen-at-the-University-of-Oklahoma |
| 9 | Roomsurf — Adams/Couch/Walker dorm reviews | Honest tower-dorm reviews vs. residential colleges | https://www.roomsurf.com/dorm-reviews/ou/adams,-couch,-and-walker-center/21369 |
| 10 | OU Parking FAQs & Policies | Permit rules, Lloyd Noble free parking + CART shuttle | https://www.ou.edu/parking/faqs-and-policies |

---

## Chunking Strategy

<!-- How will you split documents into chunks?
     State your chunk size (in tokens or characters), overlap size, and explain why those
     numbers fit the structure of your documents.
     A review-heavy corpus warrants different chunking than a long FAQ. -->

**Chunk size:** Target ~200 tokens, hard max 256 tokens.

**Overlap:** ~40 tokens, applied *only* when a single long section has to be split mid-topic — not between already-separate reviews/answers.

**Approach:** Structure-aware recursive splitting, not a blind sliding window:

1. Split each document on its natural boundaries first — paragraphs (`\n\n`), then sentences.
2. Greedily group adjacent units up to the ~200-token target.
3. Only when a *single* unit exceeds the 256-token max do we split it and add the ~40-token overlap so a tip isn't severed mid-thought.
4. Merge any leftover fragment under ~30 tokens into its neighbor so we don't embed near-empty chunks.

**Reasoning:** The corpus has two distinct shapes. (1) Long-form OU Daily columns and the official parking FAQ spread one topic across several paragraphs — the recursive split keeps a tip intact and adds overlap when a paragraph is too long. (2) Quora answers and Roomsurf reviews are self-contained, one tip per comment — splitting on boundaries first means each short review stays its own chunk with no cross-bleed from overlap. The **256-token ceiling is dictated by the embedding model**: all-MiniLM-L6-v2 truncates input past 256 tokens, so any larger chunk would lose its tail before embedding and become unretrievable. Chunks carry `source`, `url`, and `date` metadata so dated 2014–2019 advice can be distinguished from the current official FAQ at generation time.

---

## Retrieval Approach

<!-- Which embedding model are you using (e.g., all-MiniLM-L6-v2 via sentence-transformers)?
     How many chunks will you retrieve per query (top-k)?
     If you were deploying this for real users and cost wasn't a constraint, what tradeoffs
     would you weigh in choosing a different embedding model — context length, multilingual
     support, accuracy on domain-specific text, latency? -->

**Embedding model:** `all-MiniLM-L6-v2` via `sentence-transformers`. It's lightweight, runs locally with no API cost or rate limits, and produces 384-dim embeddings that are strong for short-passage semantic similarity — a good fit for a corpus of student tips and reviews. Its 256-token input ceiling is what dictates the 256-token hard max in the Chunking Strategy above, so the two sections are deliberately consistent.

**Top-k:** 4. With a small 10-source corpus chunked at ~200 tokens, k=4 gives the LLM enough surrounding context to answer questions whose evidence is spread across a couple of paragraphs (e.g. study spots cited in two different articles) without padding the prompt with weak, off-topic matches. Too few (k=1–2) risks missing the chunk that actually holds the answer; too many (k=8+) dilutes the prompt with low-relevance text the model may latch onto. I'll revisit k during evaluation if retrieval looks thin or noisy.

**Why semantic search works here:** Embeddings map text to vectors by *meaning*, not exact words, so a query like "where can I park for free" retrieves a chunk about "Lloyd Noble Center + CART shuttle" even though it shares almost no literal vocabulary with the query — exactly what's needed for paraphrased, opinion-based student language.

**Production tradeoff reflection:** If this were a real deployment and cost weren't a constraint, I'd weigh: (1) **Context length** — MiniLM truncates at 256 tokens, forcing small chunks; a model like OpenAI `text-embedding-3-large` or Voyage handles far longer inputs, so I could embed whole reviews without splitting and losing context across boundaries. (2) **Domain accuracy** — a larger or domain-tuned model would better distinguish near-synonyms ("dorm" vs "residential college") that matter in this corpus. (3) **Latency & hosting** — MiniLM is local and fast; an API-hosted model adds network latency and a per-call dependency but offloads compute. (4) **Multilingual** — not needed for an English-only OU corpus, so I wouldn't pay for it here. The net tradeoff: MiniLM is the right *free, local* choice for this project; at scale I'd move to a longer-context hosted model primarily to stop chunk-boundary information loss.

---

## Evaluation Plan

<!-- List your 5 test questions with their expected correct answers.
     Questions should be specific enough that you can judge whether the system's response
     is right or wrong. "What are good dining halls?" is too vague.
     "What do students say about wait times at [dining hall name] during lunch?" is testable. -->

| # | Question | Expected answer |
|---|----------|-----------------|
| 1 | What study spots do OU students recommend, including quieter or lesser-known ones for finals week? | Bizzell Memorial Library, Sarkeys Energy Center, the Beaird Lounge, and the Honors College are the commonly cited spots (Source 5). For finals, students point to lesser-known/quieter options beyond the main library to avoid crowds (Source 6). A good answer names at least one mainstream spot and one lesser-known spot. |
| 2 | How should a freshman manage their meal points so they don't run out before the semester ends? | Budget meal points across the semester rather than overspending early; treat them as a fixed balance and pace daily spending so they last (Sources 1 and 7). A good answer mentions pacing/budgeting and not front-loading spending. |
| 3 | Which apps do OU students consider essential? | The official OU app, Canvas (coursework/LMS), a campus map app, and transit apps are listed as must-haves (Source 3). A good answer names at least the OU app and Canvas. |
| 4 | Where can students park for free near campus, and how do they get to main campus from there? | Lloyd Noble Center offers free parking, and students take the CART shuttle to main campus (Source 10). A good answer names Lloyd Noble + the CART shuttle connection. |
| 5 | What do students honestly say about living in the Adams, Couch, and Walker tower dorms? | Candid reviews compare the older high-rise towers (Adams/Couch/Walker) against the newer residential colleges, covering tradeoffs like room size, community feel, and condition (Source 9). A good answer reflects the experiential tower-vs-residential-college comparison rather than official marketing copy. |

---

## Anticipated Challenges

<!-- What could go wrong? Name at least two specific risks with reasoning.
     Consider: noisy or inconsistent documents, missing source attribution, off-topic
     retrieval, chunks that split key information across boundaries. -->

1. **Inconsistent document structure.** The corpus mixes long-form articles with short Reddit/Quora comments, so a single chunking strategy may split long columns awkwardly while leaving short comments too sparse. Mitigation: tune chunk size/overlap per the skim notes, possibly handling the two source types differently.

2. **Dated information.** Several OU Daily columns are from 2014–2019, so specifics like parking rules, meal-plan prices, and CART transit schedules may be stale and conflict with the current official FAQ. Mitigation: anchor factual answers to the most recent official source and flag advice as experiential rather than authoritative.

---

## Architecture

<!-- Draw a diagram of your pipeline showing the five stages:
     Document Ingestion → Chunking → Embedding + Vector Store → Retrieval → Generation
     Label each stage with the tool or library you're using.
     You can use ASCII art, a Mermaid diagram, or embed a sketch as an image.
     You'll use this diagram as context when prompting AI tools to implement each stage. -->

```
                          INDEXING (offline, run once)
  ┌──────────────┐   ┌──────────────┐   ┌────────────────┐   ┌──────────────────┐
  │  1. Ingest   │──▶│  2. Chunk    │──▶│  3. Embed      │──▶│ 4. Vector Store  │
  │  documents/  │   │ structure-   │   │ all-MiniLM-    │   │   ChromaDB       │
  │  (.txt/.md/  │   │ aware split  │   │ L6-v2          │   │ PersistentClient │
  │   .html)     │   │ ~200 tok,    │   │ (sentence-     │   │ ./chroma_data    │
  │              │   │ 256 max +    │   │  transformers) │   │ + metadata:      │
  │              │   │ 40 overlap   │   │  384-dim       │   │  source/url/date │
  └──────────────┘   └──────────────┘   └────────────────┘   └────────┬─────────┘
                                                                       │
  ─────────────────────────────────────────────────────────────────  │  ──────────
                          QUERY TIME (per user question)               │
                                                                       ▼
  ┌──────────────┐   ┌────────────────┐   ┌──────────────┐   ┌──────────────────┐
  │ User query   │──▶│ Embed query    │──▶│ 5. Retrieve  │──▶│ 6. Generate      │
  │ (Gradio/     │   │ same MiniLM    │   │ top-k = 4    │   │ Groq LLM, answer │
  │  Streamlit)  │   │ model          │   │ nearest      │   │ grounded ONLY in │
  │              │◀──────────────────────────────────────── │ retrieved chunks │
  │  answer +    │   │                │   │ chunks from  │   │ + cites source   │
  │  sources     │   │                │   │ ChromaDB     │   │ metadata         │
  └──────────────┘   └────────────────┘   └──────────────┘   └──────────────────┘
```

**Stage → tool:** Ingestion = Python file reading (`pdfplumber` only if PDFs added) · Chunking = custom `chunk_text()` per Chunking Strategy · Embedding = `all-MiniLM-L6-v2` (`sentence-transformers`) · Vector store + Retrieval = **ChromaDB** local `PersistentClient` · Generation = **Groq** LLM · Interface = Gradio or Streamlit.

---

## AI Tool Plan

<!-- For each part of the pipeline below, describe:
     - Which AI tool you plan to use (Claude, Copilot, ChatGPT, etc.)
     - What you'll give it as input (which sections of this planning.md, which requirements)
     - What you expect it to produce
     - How you'll verify the output matches your spec

     "I'll use AI to help me code" is not a plan.
     "I'll give Claude my Chunking Strategy section and ask it to implement chunk_text()
     with my specified chunk size and overlap" is a plan. -->

**Milestone 3 — Ingestion and chunking:** I'll give Claude my **Chunking Strategy** section verbatim and ask it to implement two functions: `load_documents(dir)` that reads each file in `documents/` into `{text, source, url, date}` records, and `chunk_text(text, target=200, max_tokens=256, overlap=40)` that does the structure-aware recursive split I specified (paragraph → sentence → greedy group → split-with-overlap only past the 256 max → merge sub-30-token fragments). Expected output: a function returning a list of chunk dicts carrying the source/url/date metadata. I'll verify by checking that long OU Daily columns split into multiple ~200-token chunks while short Quora/Roomsurf entries each stay a single chunk, and that no chunk exceeds 256 tokens (the MiniLM ceiling).

**Milestone 4 — Embedding and retrieval:** I'll give Claude my **Retrieval Approach** section plus `chroma_example.py` as a reference and ask it to implement `build_index()` (embed all chunks with `all-MiniLM-L6-v2`, upsert into a ChromaDB `PersistentClient` collection at `./chroma_data` with metadata) and `retrieve(query, k=4)` (embed the query, return the top-4 nearest chunks with their distances and metadata). Expected output: a populated persistent collection and a retrieval function. I'll verify by running my 5 evaluation questions through `retrieve()` and confirming the returned chunks actually contain the expected-answer evidence (e.g. Q4 returns the Lloyd Noble / CART chunk).

**Milestone 5 — Generation and interface:** I'll give Claude my domain summary, the grounding requirement, and the retrieval output format, and ask it to implement `answer(query)` — assemble the top-k chunks into a context block and call the **Groq** LLM with a system prompt that instructs it to answer *only* from the provided chunks, say "I don't know based on these sources" when they don't cover the question, and cite the `source`/`url` metadata. Then a minimal **Gradio/Streamlit** UI wrapping `answer()`. Expected output: a grounded, source-citing response function plus a runnable interface. I'll verify with an out-of-domain question (e.g. "what's the football schedule?") to confirm it refuses rather than hallucinates, and by checking that in-domain answers cite a real source from my list.
