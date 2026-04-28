# Demo Script

A walkthrough of the CollectLite RAG relevance-labeling workflow.

## Setup

1. Start services: `docker-compose up`
2. Open http://localhost:3000

## Walkthrough

1. **Create project** — Click "New Project", name it "RAG Relevance Evaluation", select task type "Document Relevance Rating".
2. **Upload dataset** — Upload `data/sample_relevance_tasks.jsonl`. Confirm row preview and ingestion.
3. **Generate tasks** — Navigate to Tasks tab, pick the dataset you uploaded and the default template from the dropdowns, then click "Generate Tasks". Confirm task count matches the dataset's row count.
4. **Run model suggestions** — Click "Run Model Suggestions". Cohere Rerank scores each candidate pair.
5. **Annotate as Alice** — Open a task. Use the "Acting as:" dropdown above the annotation card to select Alice. Pick a relevance radio (relevant / partially_relevant / not_relevant), set a confidence, and submit. The Tasks queue's annotation count moves from `0/2` to `1/2`.
6. **Annotate as Bob** — Re-open the same task. Switch the "Acting as:" dropdown to Bob, choose a different label to create disagreement, and submit. The task transitions submitted → needs_review (consensus job runs in the background) and the queue badge shows `2/2`.
7. **Review disagreements** — Open Review Queue. Inspect the side-by-side annotations and model suggestion. Submit final reviewer decision.
8. **View metrics** — Open Metrics dashboard. Observe agreement rate, model-human disagreement, and throughput.
9. **Export dataset** — Click "Export", choose JSONL format. Download the file and inspect provenance fields.

## Interview Positioning

> "Based on public evidence, Cohere's Collect team builds internal human-data collection and curation workflows. I built a lower-scale version focused on the same system class: annotation task generation, model-in-the-loop suggestions, consensus, review, dashboards, and export contracts. I used a stack aligned with the Collect posting: Next.js, TypeScript, React, and Python/FastAPI."
