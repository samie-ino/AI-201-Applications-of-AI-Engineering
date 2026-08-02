# AI-201 Applications of AI Engineering

This repository contains a collection of AI engineering labs and projects completed in the AI-201 course sequence. The folders range from starter applications and agent workflows to evaluators, safety tools, and full-stack app features.

## Repository Overview

The workspace is organized into the following major components:

- `ai201-lab1-rulesbot-starter-main/` — Retrieval-augmented board game rules assistant.
- `ai201-lab2-plantadvisor-starter-master/` — Plant-care conversational agent.
- `ai201-lab3-podclassifier-starter-main/` — Few-shot podcast classifier.
- `ai201-lab4-repairsafe-starter-main/` — Safety and audit-oriented response system.
- `ai201-project1-unofficial-guide-starter/` — Retrieval-first campus guide assistant.
- `ai201-project2-fitfindr-starter-main/` — Fitness-oriented assistant or recommendation-style application.
- `ai201-project3-takemeter/` — Evaluation and modeling project centered on take-rate / recommendation analysis.
- `ai201-project4-provenance-guard/` — AI-human provenance detector with scoring, labels, and audit logging.
- `ai201-project5-mixtape-starter-copy/` — Music recommendation / playlist-oriented app starter.
- `ai201-project6-cinelog-starter-feature-watchlist/` — Film collection and watchlist application with review-driven feature work.

## What This Repo Demonstrates

Across the projects, the repository covers a broad set of AI and software engineering skills, including:

- Prompting and LLM-backed agent design
- Retrieval-augmented generation (RAG)
- Few-shot and evaluation workflows
- Safety and auditing patterns
- API and web app development
- Data ingestion, embeddings, and search
- Testing, review feedback, and feature iteration

## Suggested Workflow

1. Start with the lab or project README in the specific folder you want to work on.
2. Review the specs or planning documents before changing code.
3. Set up a Python virtual environment and install the local requirements for the target project.
4. Run the app or tests from that folder as instructed in its own README.

## General Environment Setup

Most projects follow a standard Python setup:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Some projects also rely on API keys or environment variables such as `GROQ_API_KEY` or similar configuration files.

## Notes

- Each subproject is self-contained and usually contains its own `README.md`, `requirements.txt`, and spec or test materials.
- The root of this repository is intended as a high-level index rather than a single runnable app.
- For project-specific setup, run commands inside the relevant subdirectory.

## Recommended Reading Order

If you are browsing the repository top to bottom, a practical order is:

1. `ai201-lab1-rulesbot-starter-main/`
2. `ai201-lab2-plantadvisor-starter-master/`
3. `ai201-lab3-podclassifier-starter-main/`
4. `ai201-lab4-repairsafe-starter-main/`
5. `ai201-project1-unofficial-guide-starter/`
6. `ai201-project2-fitfindr-starter-main/`
7. `ai201-project3-takemeter/`
8. `ai201-project4-provenance-guard/`
9. `ai201-project5-mixtape-starter-copy/`
10. `ai201-project6-cinelog-starter-feature-watchlist/`
