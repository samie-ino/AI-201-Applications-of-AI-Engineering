"""
train.py — Fine-tune distilbert-base-uncased to classify Stardew Valley community
posts into four functional roles (TakeMeter, Project 3).

This script is the CORRECTED training pipeline. It fixes the root causes that made
the first run collapse to a degenerate 2-class predictor (see README.md → "Root-cause
investigation"). The three fixes are called out inline with `# FIX:` comments:

  FIX 1 — Stratified split so every class (incl. the 15-example Story/Experience class)
          is represented in both train and test in proportion to the full dataset.
  FIX 2 — Class-weighted cross-entropy so the 62%-majority "Gameplay Tip" class cannot
          drown out the three minority classes and push the model into majority/near-
          majority collapse.
  FIX 3 — The label<->id mapping is written into the model config (id2label/label2id)
          AND saved to label_map.json, and evaluate.py reads it back from the model.
          This makes a train/eval label-map mismatch structurally impossible.

Run locally (CPU works for 200 examples but is slow) or on Colab with a GPU:

    pip install -r requirements.txt
    python train.py --data sources.csv --out model/

Reproducible: a fixed seed is set for numpy, torch and the split.
"""

import argparse
import json
import os
import random

import numpy as np
import pandas as pd
import torch
from sklearn.metrics import f1_score, accuracy_score
from sklearn.model_selection import train_test_split
from torch import nn
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    Trainer,
    TrainingArguments,
)

SEED = 42
BASE_MODEL = "distilbert-base-uncased"
MAX_LENGTH = 256  # post bodies are short-to-medium; 256 tokens covers the long tail


def set_seed(seed: int = SEED) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def load_dataframe(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["text"] = (df["Title"].fillna("") + ". " + df["Body"].fillna("")).str.strip(". ")
    df["label_str"] = df["Label"].str.strip()
    df = df[df["label_str"].notna() & (df["label_str"] != "")].reset_index(drop=True)
    return df


class WeightedTrainer(Trainer):
    """Trainer that applies per-class weights to the loss (FIX 2)."""

    def __init__(self, *args, class_weights=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.class_weights = class_weights

    def compute_loss(self, model, inputs, return_outputs=False, **kwargs):
        labels = inputs.pop("labels")
        outputs = model(**inputs)
        loss_fct = nn.CrossEntropyLoss(weight=self.class_weights.to(outputs.logits.device))
        loss = loss_fct(outputs.logits, labels)
        return (loss, outputs) if return_outputs else loss


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="sources.csv")
    ap.add_argument("--out", default="model")
    ap.add_argument("--epochs", type=int, default=10)
    ap.add_argument("--lr", type=float, default=2e-5)
    ap.add_argument("--batch_size", type=int, default=8)
    ap.add_argument("--test_size", type=int, default=30)
    args = ap.parse_args()

    set_seed()
    df = load_dataframe(args.data)

    # Stable, sorted label map so it never depends on row order (FIX 3).
    labels = sorted(df["label_str"].unique())
    label2id = {l: i for i, l in enumerate(labels)}
    id2label = {i: l for l, i in label2id.items()}
    df["label"] = df["label_str"].map(label2id)
    print("Label map:", label2id)
    print("Full distribution:\n", df["label_str"].value_counts())

    # FIX 1: stratified split — keeps all four classes in train AND test.
    train_df, test_df = train_test_split(
        df,
        test_size=args.test_size,
        random_state=SEED,
        stratify=df["label"],
    )
    print("\nTest-set distribution (stratified):\n", test_df["label_str"].value_counts())

    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)

    def tokenize(batch_texts):
        return tokenizer(
            list(batch_texts),
            truncation=True,
            padding="max_length",
            max_length=MAX_LENGTH,
        )

    class DS(torch.utils.data.Dataset):
        def __init__(self, frame):
            self.enc = tokenize(frame["text"].tolist())
            self.labels = frame["label"].tolist()

        def __len__(self):
            return len(self.labels)

        def __getitem__(self, i):
            item = {k: torch.tensor(v[i]) for k, v in self.enc.items()}
            item["labels"] = torch.tensor(self.labels[i])
            return item

    train_ds, test_ds = DS(train_df), DS(test_df)

    # FIX 2: inverse-frequency class weights.
    counts = train_df["label"].value_counts().sort_index().values
    class_weights = torch.tensor(counts.sum() / (len(counts) * counts), dtype=torch.float)
    print("\nClass weights (inverse frequency):", dict(zip(labels, class_weights.tolist())))

    # FIX 3: id2label/label2id baked into the model config and persisted.
    model = AutoModelForSequenceClassification.from_pretrained(
        BASE_MODEL,
        num_labels=len(labels),
        id2label=id2label,
        label2id=label2id,
    )

    def metrics(eval_pred):
        logits, y = eval_pred
        preds = np.argmax(logits, axis=-1)
        return {
            "accuracy": accuracy_score(y, preds),
            "macro_f1": f1_score(y, preds, average="macro", zero_division=0),
        }

    targs = TrainingArguments(
        output_dir=os.path.join(args.out, "_checkpoints"),
        num_train_epochs=args.epochs,
        learning_rate=args.lr,
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=args.batch_size,
        weight_decay=0.01,
        warmup_ratio=0.1,
        eval_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
        metric_for_best_model="macro_f1",  # select on macro-F1, not accuracy (imbalance)
        greater_is_better=True,
        logging_steps=10,
        seed=SEED,
    )

    trainer = WeightedTrainer(
        model=model,
        args=targs,
        train_dataset=train_ds,
        eval_dataset=test_ds,
        compute_metrics=metrics,
        class_weights=class_weights,
    )
    trainer.train()

    os.makedirs(args.out, exist_ok=True)
    trainer.save_model(args.out)
    tokenizer.save_pretrained(args.out)
    with open(os.path.join(args.out, "label_map.json"), "w") as f:
        json.dump({"label2id": label2id, "id2label": id2label}, f, indent=2)

    # Persist exactly which rows were held out so evaluate.py scores the SAME test set.
    test_df[["Source Number", "text", "label_str", "label"]].to_csv(
        os.path.join(args.out, "test_set.csv"), index=False
    )
    print(f"\nSaved model + label_map.json + test_set.csv to {args.out}/")


if __name__ == "__main__":
    main()
