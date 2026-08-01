# Architecture and Planning

## 1. Architecture Narrative
**The path of a submission:**
When a piece of text is submitted, it hits the `POST /submit` endpoint, which first checks the **Rate Limiter** to ensure the user hasn't exceeded their allowed request quota. If approved, the raw text is passed to the **Multi-Signal Detection Pipeline**. 

Inside the pipeline, the text is evaluated independently by two components: **Signal 1** and **Signal 2**. Each signal returns an independent score. These scores are routed to the **Scoring Engine**, which weighs the signals and calculates a combined `confidence score` (ranging from 0.0 to 1.0). 

This score is then passed to the **Label Generator**, which maps the numeric confidence to one of three plain-language transparency labels (e.g., High-Confidence Human, Uncertain, High-Confidence AI). Finally, the entire payload (the text, individual signal scores, final confidence score, and generated label) is written to the **Audit Logger** for record-keeping. The system then returns a JSON response to the user containing the attribution result, confidence score, and transparency label.

## 2. Detection Signals
To differentiate between human and AI writing, the detection pipeline will use the following two signals:

**Signal 1: Text Predictability (Perplexity)**
*   **What it measures:** How predictable the word choices are based on common language patterns.
*   **Why it differs:** Large Language Models inherently predict the "most likely" next word, resulting in highly probable word choices. Humans use quirkier, less predictable vocabulary.
*   **Blind spot:** Highly technical writing, legal documents, or formal academic text often use highly predictable, standardized language. This signal will likely flag formal human writing as AI.

**Signal 2: Sentence Variation (Burstiness)**
*   **What it measures:** The variation in sentence length and structure throughout the text.
*   **Why it differs:** Humans naturally write in "bursts"—mixing very short, punchy sentences with long, complex, run-on sentences. AI models tend to produce sentences with a highly uniform length and rhythmic structure.
*   **Blind spot:** A human who writes very methodically (like a technical manual writer or a young student learning basic essay structure) will have low burstiness, causing this signal to falsely identify their work as AI.

## 3. Flow Diagrams

**Submission Flow**

[Client] 
   │ 
   ▼ (POST /submit: raw text)
[Rate Limiter] ──(rejected)──> 429 Error
   │ 
   ▼ (approved text)
[Detection Pipeline] 
   ├──> Signal 1 (Predictability) ──┐
   └──> Signal 2 (Burstiness) ──────┴──> (signal scores)
                                              │
                                              ▼
[Scoring Engine] ────────(confidence score)──>│
                                              ▼
[Label Generator] ──────(transparency label)─>│
                                              ▼
[Audit Logger] <──(saves text, scores, label)─┘
   │
   ▼
[Client Response] (attribution, score, label)


**Appeal Flow**

[Client]
   │
   ▼ (POST /appeal: submission_id, reasoning)
[Appeals Workflow] 
   │
   ├─(1. updates status to "Under Review")
   │
   ▼ (status & reasoning)
[Audit Logger] <──(appends appeal to original log entry)
   │
   ▼
[Client Response] (status updated confirmation)