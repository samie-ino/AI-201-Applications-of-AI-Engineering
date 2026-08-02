"""
Grounded generation for The Unofficial Guide (OU campus survival).

Milestone 5: take a user question, retrieve the top-k chunks from ChromaDB
(Milestone 4), assemble them into a context block, and ask a Groq-hosted LLM
to answer using ONLY that context — citing the source metadata and refusing
when the sources don't cover the question.

See planning.md "AI Tool Plan" (Milestone 5) for the spec this implements.

Requires GROQ_API_KEY in the environment or a .env file (see .env.example).
Run `python generate.py` to answer the 5 evaluation questions from the CLI.
"""

import os
import textwrap

from dotenv import load_dotenv
from groq import Groq

from embed import retrieve

load_dotenv()

# Overridable so the model can be swapped without touching code.
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

# The grounding contract. The model is told, explicitly, that the numbered
# sources are its ONLY allowed knowledge and exactly what to do when they fall
# short — this is what stops it from answering an out-of-domain question from
# its own pretraining instead of refusing.
SYSTEM_PROMPT = textwrap.dedent("""\
    You are The Unofficial Guide, a helpful assistant for University of
    Oklahoma (Norman) students. You answer using ONLY the numbered sources
    provided in the user's message — student articles, reviews, and the
    official parking FAQ.

    Rules:
    - Base every claim strictly on the provided sources. Do not use outside
      knowledge, and do not guess.
    - If the sources do not contain the answer, reply exactly:
      "I don't know based on these sources." Do not pad it with a guess.
    - Cite the sources you used by their number, like [1] or [2][3], placed
      right after the claim they support.
    - Some advice is dated student opinion (note the year) and some is the
      current official policy. When they could conflict, prefer the official
      source for facts (rules, prices, locations) and clearly frame student
      tips as opinion.
    - Keep answers concise and practical — a few sentences, not an essay.""")

# Filter out chunks the retriever returned but that are only weakly related.
# Past this cosine distance a "match" is usually off-topic noise that would
# only mislead the model (see Milestone 4 — good matches sit well under 0.5).
MAX_DISTANCE = 0.6


def _format_context(hits):
    """Render retrieved chunks as a numbered source list for the prompt.

    Each entry carries source name + date + url so the model can cite it and
    so we can weight official vs. dated-opinion sources per the system prompt.
    """
    blocks = []
    for i, h in enumerate(hits, 1):
        header = f"[{i}] {h['source'] or h['filename']}"
        if h.get("date"):
            header += f" (dated {h['date']})"
        if h.get("url"):
            header += f"\n    url: {h['url']}"
        blocks.append(f"{header}\n{h['text']}")
    return "\n\n".join(blocks)


def answer(query, k=4):
    """Answer `query` grounded only in the top-k retrieved chunks.

    Returns a dict: {"answer", "sources", "hits"} where `sources` is the
    deduplicated list of source/url/date actually placed in the context (for
    UI attribution) and `hits` is the raw retrieval output (for debugging).
    """
    hits = retrieve(query, k=k)
    # Drop weak matches so a single noisy chunk can't pull the answer off-topic.
    hits = [h for h in hits if h["distance"] <= MAX_DISTANCE]

    if not hits:
        return {
            "answer": "I don't know based on these sources.",
            "sources": [],
            "hits": [],
        }

    context = _format_context(hits)
    user_msg = (
        f"Sources:\n\n{context}\n\n"
        f"Question: {query}\n\n"
        "Answer using only the sources above, citing them by number."
    )

    client = Groq(api_key=os.environ["GROQ_API_KEY"])
    completion = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ],
        temperature=0.2,  # low: stay close to the sources, minimal embellishment
    )
    text = completion.choices[0].message.content.strip()

    # If the model refused (sources didn't cover the question), don't attribute
    # the non-answer to the retrieved-but-unused chunks.
    if text.lower().startswith("i don't know based on these sources"):
        return {"answer": text, "sources": [], "hits": hits}

    # Deduplicate sources by url (fall back to filename) for clean attribution.
    seen, sources = set(), []
    for h in hits:
        key = h.get("url") or h["filename"]
        if key not in seen:
            seen.add(key)
            sources.append({
                "source": h["source"] or h["filename"],
                "url": h["url"],
                "date": h["date"],
            })

    return {"answer": text, "sources": sources, "hits": hits}


# The 5 evaluation questions from planning.md, plus one out-of-domain probe to
# confirm the model refuses instead of hallucinating.
_EVAL_QUESTIONS = [
    "What study spots do OU students recommend, including quieter or lesser-known ones for finals week?",
    "How should a freshman manage their meal points so they don't run out before the semester ends?",
    "Which apps do OU students consider essential?",
    "Where can students park for free near campus, and how do they get to main campus from there?",
    "What do students honestly say about living in the Adams, Couch, and Walker tower dorms?",
    "What is the OU football schedule this season?",  # out-of-domain: should refuse
]


def _run_eval():
    for q in _EVAL_QUESTIONS:
        print("=" * 78)
        print(f"Q: {q}")
        print("-" * 78)
        result = answer(q)
        print(result["answer"])
        if result["sources"]:
            print("\nSources:")
            for s in result["sources"]:
                line = f"  - {s['source']}"
                if s["date"]:
                    line += f" ({s['date']})"
                if s["url"]:
                    line += f"\n    {s['url']}"
                print(line)
        print()


if __name__ == "__main__":
    _run_eval()
