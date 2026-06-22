## Community: 
**Stardew Valley players** — a farming/life-simulation game community spread across Reddit (r/StardewValley), the Official Stardew Valley Forums, Steam Community discussions, Fandom Wiki talk pages, GameFAQs boards, and Discord servers.

This community is a good fit for a classification task because its posts fall into clearly distinct functional roles: players ask questions when they are stuck, share tips when they have learned something, tell stories about their farms and moments, and debate opinions about mechanics and playstyle choices. These roles are recognizable to any community member and map naturally onto labels.

The discourse is varied enough to be interesting because the game has a large range of experience levels (first-day beginners through completionists chasing 100% perfection), a wide topic space (farming, mining, fishing, combat, NPCs, mods, seasonal events), and a mix of practical and emotional engagement — meaning posts range from dry mechanical questions to enthusiastic storytelling and heated debates about things like whether the Joja route is morally acceptable.

## Labels: 

**Gameplay Tip** — A post whose primary function is delivering actionable strategy, mechanics information, or how-to guidance that another player can directly act on.
- *Example 1 (Source 6):* "Hold seed bags to replant the tiles simultaneously, saving time. Junimos can phase through trellis crops to harvest, so you can plant them without gaps. Remember they don't harvest when it's raining."
- *Example 2 (Source 20):* "Don't donate your first prismatic shard or dinosaur egg to the museum! Use the shard in the desert for the galaxy sword, and put the dino egg in an incubator. You can donate the next ones you find."

**Question** — A post asking for specific information, clarification, a recommendation, or help solving a concrete problem.
- *Example 1 (Source 25):* "Does anyone know if pigs still find truffles in the winter? Trying to plan out my artisan goods for next season but I'm broke right now."
- *Example 2 (Source 57):* "hello, I need hardwood for the house upgrade and I need to get it quickly what would be the faster way to get it?"

**Story / Experience** — A post sharing a personal gameplay moment — an achievement, accident, discovery, frustration, or real-life connection to the game — where the primary purpose is to relate what happened rather than to advise or debate.
- *Example 1 (Source 17):* "Finally made it to level 100 in Skull Cavern! I didn't think I was ever going to do it. I brought 100 mega bombs, a huge stack of cheese, and 30 staircases just in case."
- *Example 2 (Source 89):* "IRL pic of some salmonberries I found while hiking! They look exactly like the ones in the game. I almost expected to hear the little pop sound effect when I picked them."

**Opinion / Discussion** — A post expressing a preference, comparison, or hot take, or opening a community debate where there is no single correct answer.
- *Example 1 (Source 19):* "Who is the best roommate and why is it Krobus? Title says it all. He doesn't get jealous, gives you void eggs, and his room matches the aesthetic of my dark wizard farm perfectly."
- *Example 2 (Source 77):* "Please read the wiki. I've been noticing lots of people in the sub asking questions about Stardew Valley that could easily be answered using the wiki or just by doing a quick google search."

## Hard edge cases: 

**Story framing a Tip** — Some posts open with a personal mishap or discovery and then pivot to advice (e.g. Source 22: "I accidentally blew up my mayo machines — PSA: do not put your bombs on your hotbar when doing farm chores"). The story is the vehicle; the tip is the point. *Rule:* if the post explicitly states advice or a warning the reader should act on, label it **Gameplay Tip**.

**Question vs. Opinion / Discussion** — Some posts are phrased as questions but are really inviting debate rather than seeking a factual answer (e.g. Source 116: "Is the Joja route actually better for min-maxing?" or Source 133: "Trout Derby vs SquidFest — which is better?"). *Rule:* if the post has a single correct or well-established answer, label it **Question**; if it is comparing options where preference and playstyle determine the answer, label it **Opinion / Discussion**.

**Gameplay Tip softened with "imo"** — Some tips are hedged with opinion language (e.g. Source 3: "imo ancient fruit is more profitable in the long run bc they continue to produce without needing to be replanted"). *Rule:* if the content is concrete and actionable regardless of the hedging language, label it **Gameplay Tip**.

## Data collection plan: 
Examples were collected from six platforms where Stardew Valley players actively post: Reddit (r/StardewValley), the Official Stardew Valley Forums (forums.stardewvalley.net), Steam Community discussions, Fandom Wiki talk pages, GameFAQs boards, and Discord servers. Posts and comments were selected manually by browsing threads across all six platforms, targeting a mix of experience levels (beginner, mid-game, late-game) and topics (farming, fishing, mining, NPCs, mods, seasonal events).

The final dataset contains 200 labeled examples with the following distribution:

| Label | Count | % |
|---|---|---|
| Gameplay Tip | 124 | 62% |
| Question | 35 | 17.5% |
| Opinion / Discussion | 26 | 13% |
| Story / Experience | 15 | 7.5% |

**Story / Experience is underrepresented** at 15 examples (7.5%). This reflects how the community actually communicates — tips and questions dominate — so the imbalance is real rather than a collection error. To handle it during evaluation, macro F1 will be used as the primary metric so that the minority class is not drowned out by the majority. If the Story / Experience class performs too poorly (F1 below 0.50), additional examples will be collected by specifically targeting achievement posts and personal gameplay moment threads.

## Evaluation metrics: 
**Primary metric: macro F1.** Because the dataset is class-imbalanced (Gameplay Tip makes up 62% of examples), accuracy alone is misleading — a model that predicts "Gameplay Tip" for everything would score 62% accuracy while being completely useless on the other three labels. Macro F1 averages the F1 score for each label without weighting by class size, so the model is held equally accountable for its performance on Story / Experience (15 examples) as it is for Gameplay Tip (124 examples).

**Per-class precision and recall.** Macro F1 summarizes performance but hides which labels the model struggles with. Reporting precision and recall separately for each class makes it possible to see, for example, whether the model confuses Question with Gameplay Tip (a likely failure mode, since answers to questions are tips). A confusion matrix will be included to visualize the off-diagonal errors.

**Weighted F1 (secondary).** Weighted F1 accounts for class frequency and reflects real-world performance if the classifier is deployed on naturally occurring community posts. It is reported alongside macro F1 so both perspectives are visible.

## Definition of success: 
**Genuinely useful:** A macro F1 of 0.75 or above across all four labels would indicate the classifier generalizes beyond the majority class and can reliably distinguish Questions from Tips, and both from Stories and Opinions. At that level, the classifier could usefully power features like surfacing unanswered questions to experienced players or indexing tips by topic.

**Good enough for deployment:** A macro F1 of 0.65 or above, with no individual label falling below F1 = 0.50. The Story / Experience class is the hardest to hit given its small size, so a floor of 0.50 F1 on that label is the minimum before the classifier would be trusted to label new community posts without human review. Below that threshold, the classifier would need either more training data for the minority class or a fallback to human annotation for posts it is uncertain about.

## AI Tool Plan

This project produces no code to generate, so AI tools are used at three points in the
annotation-and-evaluation workflow: stress-testing my labels before I annotate, optionally
pre-labeling a batch, and finding patterns in my model's errors after evaluation.

### 1. Source discovery (before data collection)
**Goal:** Identify platforms and community threads likely to contain on-topic posts.

- **Tool:** Google Gemini.
- **What I asked for:** websites and forum threads where players discuss Stardew Valley gameplay.
- **What I used it for:** Gemini surfaced the platforms (Reddit, Steam Community, Official Forums, Fandom Wiki, GameFAQs, Discord). It did not select any individual posts or comments.
- **What I did myself:** I browsed each platform and manually chose which specific posts and comments to include in the dataset. All 200 examples are posts I personally selected and read.

### 2. Data organization (before annotation)
**Goal:** Structure raw source text into a clean, labeled CSV ready for annotation.

- **Tool:** Claude (Sonnet 4.6) via Claude Code.
- **What I gave it:** raw source text with all entries packed into unstructured cells, including merged rows, restarted numbering, and prose notes mixed into the file.
- **What I asked for:** split each source into its own row, assign consistent columns (Source Number, Platform, Type, Title, Body), fix merged/duplicate rows, renumber sequentially, and add an empty Label column.
- **What I did myself:** all source selection and content came from me. Claude only reformatted the data I had already collected — it did not add, remove, or change any post or comment text.

### 3. Label stress-testing (before annotation)
**Goal:** Confirm my label definitions are tight enough to apply consistently *before* I commit
to annotating 200 examples.

- **Tool:** Claude (Sonnet 4.6).
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

### 4. Annotation (labeling all 200 sources)
**Decision:** Yes — Claude pre-labeled all 200 examples.

- **Tool:** Claude (Sonnet 4.6) via Claude Code.
- **What I gave it:** the four label definitions (Gameplay Tip, Question, Story / Experience, Opinion / Discussion) and all 200 source rows from sources.csv.
- **What Claude did:** assigned one label to each of the 200 rows based on the primary function of the post text. The resulting distribution was: Gameplay Tip (124), Question (35), Opinion / Discussion (26), Story / Experience (15).
- **What I still need to do:** review every label Claude assigned and correct any I disagree with. Claude's label is a starting point, not the final answer — I am responsible for the annotation quality.

### 5. Failure analysis (after evaluation)
**Goal:** Find structure in my model's mistakes before I write up the evaluation, rather than
eyeballing rows.

- **Tool:** Claude (Sonnet 4.6).
- **What I'll give it:** the list of wrong predictions — each with the post text, the true label,
  and the predicted label (effectively the off-diagonal cells of my confusion matrix).
- **What I'll ask for:** patterns in the errors — e.g. which label pair is most often confused,
  whether errors cluster by post length, topic, tone/sarcasm, or a recurring phrasing.
- **How I'll verify:** I treat any pattern as a *hypothesis*, not a finding. For each claimed
  pattern I'll go back to the actual misclassified posts and confirm it holds (and check it isn't
  also true of correctly-classified posts). Only verified patterns go into the evaluation report,
  and I'll cite the specific examples that support each one.
