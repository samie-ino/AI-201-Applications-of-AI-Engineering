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

**Chunk size:** _(TBD in Milestone 2 — likely ~400–600 tokens)_

**Overlap:** _(TBD — likely ~50–100 tokens)_

**Reasoning:** Skim notes — the corpus has two distinct shapes. (1) Long-form OU Daily columns and the official parking FAQ spread one topic across several paragraphs, which favors larger chunks with overlap so a single tip isn't split mid-thought. (2) Reddit comments, Quora answers, and Roomsurf reviews are self-contained, one tip per comment, which favors smaller chunks (roughly one comment = one chunk). Final numbers to be confirmed after fully reading the documents in Milestone 2.

---

## Retrieval Approach

<!-- Which embedding model are you using (e.g., all-MiniLM-L6-v2 via sentence-transformers)?
     How many chunks will you retrieve per query (top-k)?
     If you were deploying this for real users and cost wasn't a constraint, what tradeoffs
     would you weigh in choosing a different embedding model — context length, multilingual
     support, accuracy on domain-specific text, latency? -->

**Embedding model:**

**Top-k:**

**Production tradeoff reflection:**

---

## Evaluation Plan

<!-- List your 5 test questions with their expected correct answers.
     Questions should be specific enough that you can judge whether the system's response
     is right or wrong. "What are good dining halls?" is too vague.
     "What do students say about wait times at [dining hall name] during lunch?" is testable. -->

| # | Question | Expected answer |
|---|----------|-----------------|
| 1 | | |
| 2 | | |
| 3 | | |
| 4 | | |
| 5 | | |

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

**Milestone 3 — Ingestion and chunking:**

**Milestone 4 — Embedding and retrieval:**

**Milestone 5 — Generation and interface:**
