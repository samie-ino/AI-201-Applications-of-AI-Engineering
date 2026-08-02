"""
Gradio chat interface for The Unofficial Guide (OU campus survival).

Milestone 5: a minimal UI wrapping generate.answer() so a user can ask a
question and get a grounded, source-cited response.

Run `python app.py`, then open the printed local URL. The ChromaDB index must
already be built (run `python embed.py` first) and GROQ_API_KEY must be set.
"""

import gradio as gr

from generate import answer

EXAMPLES = [
    "Where can I study during finals week if the main library is packed?",
    "How do I make my meal points last the whole semester?",
    "Which apps should I download as a new OU student?",
    "Where can I park for free and get to main campus?",
    "Are the Adams/Couch/Walker towers a good place to live?",
]


def _respond(message, history):
    """Gradio chat callback: answer the message and append a sources footer."""
    result = answer(message)
    reply = result["answer"]

    if result["sources"]:
        lines = ["", "---", "**Sources:**"]
        for s in result["sources"]:
            label = s["source"]
            if s["date"]:
                label += f" ({s['date']})"
            lines.append(f"- [{label}]({s['url']})" if s["url"] else f"- {label}")
        reply += "\n".join(lines)
    return reply


demo = gr.ChatInterface(
    fn=_respond,
    title="The Unofficial Guide — OU Campus Survival",
    description=(
        "Ask about study spots, meal plans, dorms, parking, apps, and freshman "
        "tips. Answers come only from collected student articles, reviews, and "
        "the official OU parking FAQ — with sources cited."
    ),
    examples=EXAMPLES,
)

if __name__ == "__main__":
    demo.launch()
