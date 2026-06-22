## Community: 
What community did you choose and why? 
Why is this community a good fit for a classification task?
What makes the discourse varied enough to be interesting?

## Labels: 
What are your 2–4 labels? Define each in a complete sentence. Include 2 example posts per label.

## Hard edge cases: 
What type of post will be genuinely ambiguous between two labels? 
How will you handle it when you encounter it during annotation?

## Data collection plan: 
Where will you collect examples? How many per label? 
What will you do if a label is underrepresented after 200 examples?

## Evaluation metrics: 
Which metrics will you use to evaluate your model and why are those the right ones for this specific task? (Accuracy alone is not enough — explain what else you need and why.)

## Definition of success: 
What performance would make this classifier genuinely useful? 
What would you accept as "good enough" for deployment in a real community tool?

## AI Tool Plan

This project produces no code to generate, so AI tools are used at three points in the
annotation-and-evaluation workflow: stress-testing my labels before I annotate, optionally
pre-labeling a batch, and finding patterns in my model's errors after evaluation.

### 1. Label stress-testing (before annotation)
**Goal:** Confirm my label definitions are tight enough to apply consistently *before* I commit
to annotating 200 examples.

- **Tool:** Claude (Opus 4.8).
- **What I'll give it:** my full label definitions, the example posts for each label, and my
  "hard edge cases" description.
- **What I'll ask for:** 5–10 synthetic posts that deliberately sit on the boundary between two
  labels (especially the pair I expect to be most confusable).
- **How I'll use the output:** I'll try to classify each generated post myself. Any post I *can't*
  assign cleanly is a signal that my definitions overlap or leave a gap — I'll tighten the wording,
  add a tie-breaker rule, or merge/split a label, and re-run the test until the boundary posts are
  classifiable.
- **Caveat:** these are synthetic posts for testing definitions only — they will **not** enter my
  real labeled dataset.

### 2. Annotation assistance (during annotation)
**Decision:** [ Yes — I will pre-label / No — I will hand-label everything ] *(choose one)*

If pre-labeling:
- **Tool:** Claude (Opus 4.8), given the same label definitions used above.
- **Process:** the model proposes a label for a batch; I review and correct every example myself.
  The model's label is a suggestion, never the final label.
- **Tracking for disclosure:** I'll add a `pre_labeled` (true/false) column and an
  `ai_label` column to my dataset so I can report exactly which examples were AI-suggested, how
  often I overrode the suggestion, and which labels the model handled poorly. This goes in my
  AI usage section.

If hand-labeling: I'll note that no AI was used in annotation, so all 200 labels are my own
judgment.

### 3. Failure analysis (after evaluation)
**Goal:** Find structure in my model's mistakes before I write up the evaluation, rather than
eyeballing rows.

- **Tool:** Claude (Opus 4.8).
- **What I'll give it:** the list of wrong predictions — each with the post text, the true label,
  and the predicted label (effectively the off-diagonal cells of my confusion matrix).
- **What I'll ask for:** patterns in the errors — e.g. which label pair is most often confused,
  whether errors cluster by post length, topic, tone/sarcasm, or a recurring phrasing.
- **How I'll verify:** I treat any pattern as a *hypothesis*, not a finding. For each claimed
  pattern I'll go back to the actual misclassified posts and confirm it holds (and check it isn't
  also true of correctly-classified posts). Only verified patterns go into the evaluation report,
  and I'll cite the specific examples that support each one.
