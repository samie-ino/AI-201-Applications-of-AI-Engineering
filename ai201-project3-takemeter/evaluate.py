"""
evaluate.py — Evaluate the fine-tuned classifier against the Groq LLM baseline on the
SAME held-out test set, and emit a full report (TakeMeter, Project 3).

Outputs:
  - evaluation_results.json   overall + per-class metrics for both models
  - confusion_matrix.png      fine-tuned model confusion matrix
  - wrong_predictions.json    every misclassified test example (text, true, pred) for
                              error analysis — so surprising metrics can be DEBUGGED,
                              not just reported.

Critically, the label mapping is read back from the fine-tuned model's own config
(model.config.id2label). The eval code never hard-codes a label order, so a
train/eval label-map mismatch cannot happen here.

    python evaluate.py --model model/ --test model/test_set.csv

The baseline needs GROQ_API_KEY (in a .env file or the environment). If it is absent
the script still evaluates the fine-tuned model and skips the baseline with a warning.
"""

import argparse
import json
import os

import numpy as np
import pandas as pd
import torch
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    f1_score,
    accuracy_score,
)
from transformers import AutoModelForSequenceClassification, AutoTokenizer

# ---- Baseline prompt (documented in README.md → "Baseline") --------------------------
BASELINE_SYSTEM = """You are a classifier for posts from the Stardew Valley player community.
Assign each post EXACTLY ONE of these four labels based on its PRIMARY function:

- "Gameplay Tip": delivers actionable strategy, mechanics info, or how-to guidance the
  reader can directly act on. If the post states advice or a warning, choose this even if
  it is wrapped in a story or hedged with "imo".
- "Question": asks for specific information, a recommendation, or help with a concrete
  problem that has a single correct or well-established answer.
- "Story / Experience": relates a personal gameplay moment (achievement, accident,
  discovery, frustration, real-life tie-in); the point is what happened, not to advise.
- "Opinion / Discussion": expresses a preference/hot take or opens a debate where
  playstyle determines the answer. A post phrased as a question but comparing options by
  preference belongs here, not in Question.

Respond with ONLY the label text, nothing else."""

BASELINE_USER = 'Classify this post:\n\n"""{text}"""'


def predict_finetuned(model_dir, texts):
    tok = AutoTokenizer.from_pretrained(model_dir)
    model = AutoModelForSequenceClassification.from_pretrained(model_dir)
    model.eval()
    id2label = {int(k): v for k, v in model.config.id2label.items()}  # source of truth
    preds = []
    with torch.no_grad():
        for t in texts:
            enc = tok(t, truncation=True, padding=True, max_length=256, return_tensors="pt")
            logits = model(**enc).logits
            preds.append(id2label[int(logits.argmax(-1))])
    return preds, id2label


def predict_baseline(texts, labels):
    """Zero-shot LLM baseline via Groq. Returns None if no API key is configured."""
    try:
        from dotenv import load_dotenv
        load_dotenv()
        from groq import Groq
    except ImportError:
        print("groq/python-dotenv not installed — skipping baseline.")
        return None
    if not os.getenv("GROQ_API_KEY"):
        print("GROQ_API_KEY not set — skipping baseline.")
        return None

    client = Groq()
    preds = []
    for t in texts:
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            temperature=0,
            messages=[
                {"role": "system", "content": BASELINE_SYSTEM},
                {"role": "user", "content": BASELINE_USER.format(text=t)},
            ],
        )
        out = resp.choices[0].message.content.strip().strip('"')
        # snap free-text output to the closest known label
        preds.append(next((l for l in labels if l.lower() in out.lower()), labels[0]))
    return preds


def per_class(y_true, y_pred, labels):
    rep = classification_report(
        y_true, y_pred, labels=labels, output_dict=True, zero_division=0
    )
    return {l: {"precision": rep[l]["precision"], "recall": rep[l]["recall"],
                "f1": rep[l]["f1-score"], "support": rep[l]["support"]} for l in labels}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="model")
    ap.add_argument("--test", default="model/test_set.csv")
    args = ap.parse_args()

    test = pd.read_csv(args.test)
    texts = test["text"].tolist()
    y_true = test["label_str"].tolist()

    ft_pred, id2label = predict_finetuned(args.model, texts)
    labels = [id2label[i] for i in sorted(id2label)]

    results = {"test_set_size": len(texts), "label_map": {v: k for k, v in id2label.items()}}

    def block(name, y_pred):
        results[name] = {
            "accuracy": round(accuracy_score(y_true, y_pred), 4),
            "macro_f1": round(f1_score(y_true, y_pred, average="macro", labels=labels, zero_division=0), 4),
            "weighted_f1": round(f1_score(y_true, y_pred, average="weighted", labels=labels, zero_division=0), 4),
            "per_class": per_class(y_true, y_pred, labels),
        }

    block("finetuned", ft_pred)

    base_pred = predict_baseline(texts, labels)
    if base_pred is not None:
        block("baseline", base_pred)
        results["improvement"] = round(
            results["finetuned"]["accuracy"] - results["baseline"]["accuracy"], 4
        )

    # Confusion matrix for the fine-tuned model
    cm = confusion_matrix(y_true, ft_pred, labels=labels)
    try:
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(8, 6))
        im = ax.imshow(cm, cmap="Blues")
        ax.set_xticks(range(len(labels)), labels, rotation=20, ha="right")
        ax.set_yticks(range(len(labels)), labels)
        for i in range(len(labels)):
            for j in range(len(labels)):
                ax.text(j, i, cm[i, j], ha="center",
                        color="white" if cm[i, j] > cm.max() / 2 else "black")
        ax.set_xlabel("Predicted label"); ax.set_ylabel("True label")
        ax.set_title("Fine-Tuned Model — Confusion Matrix (Test Set)")
        fig.tight_layout(); fig.savefig("confusion_matrix.png", dpi=120)
        print("Wrote confusion_matrix.png")
    except ImportError:
        print("matplotlib not installed — skipped confusion_matrix.png")

    # Dump every wrong prediction for error analysis
    wrong = [
        {"text": t, "true": yt, "pred": yp}
        for t, yt, yp in zip(texts, y_true, ft_pred) if yt != yp
    ]
    with open("wrong_predictions.json", "w") as f:
        json.dump(wrong, f, indent=2)

    with open("evaluation_results.json", "w") as f:
        json.dump(results, f, indent=2)

    print(json.dumps(results, indent=2))
    print(f"\n{len(wrong)} wrong predictions saved to wrong_predictions.json")


if __name__ == "__main__":
    main()
