"""
app.py — Gradio demo interface for the fine-tuned TakeMeter classifier.

Loads the fine-tuned model from ./model and classifies a pasted Stardew Valley post,
showing the predicted label and the full softmax confidence over all four classes.
The label mapping comes from the model config (model.config.id2label) — never hard-coded.

    python app.py
"""

import gradio as gr
import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

MODEL_DIR = "model"

tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR)
model = AutoModelForSequenceClassification.from_pretrained(MODEL_DIR)
model.eval()
id2label = {int(k): v for k, v in model.config.id2label.items()}


def classify(text: str):
    if not text.strip():
        return {}
    enc = tokenizer(text, truncation=True, padding=True, max_length=256, return_tensors="pt")
    with torch.no_grad():
        probs = torch.softmax(model(**enc).logits, dim=-1)[0]
    return {id2label[i]: float(probs[i]) for i in range(len(id2label))}


demo = gr.Interface(
    fn=classify,
    inputs=gr.Textbox(lines=6, label="Stardew Valley post", placeholder="Paste a post…"),
    outputs=gr.Label(num_top_classes=4, label="Predicted role (with confidence)"),
    title="TakeMeter — Stardew Valley Post Classifier",
    description="Classifies a community post as Gameplay Tip, Question, Story / Experience, "
                "or Opinion / Discussion.",
    examples=[
        ["Hold seed bags to replant the tiles simultaneously. Junimos phase through trellis crops."],
        ["I need hardwood for the house upgrade quickly — what's the fastest way to get it?"],
        ["I accidentally blew up my only mineral copier. Instant restart."],
        ["Who is the best roommate and why is it Krobus? He gives you void eggs and never gets jealous."],
    ],
)

if __name__ == "__main__":
    demo.launch()
