# Demo Script

A walkthrough of the CollectLite RAG relevance-labeling workflow.

## Setup

1. Start services: `docker-compose up`
2. Open http://localhost:3000

## Walkthrough

1. **Create project** — Click "New Project", name it "RAG Relevance Evaluation", select task type "Document Relevance Rating".
2. **Upload dataset** — Upload `data/sample_relevance_tasks.jsonl`. Confirm row preview and ingestion.
3. **Generate tasks** — Navigate to Tasks tab, click "Generate Tasks". Confirm task count matches row count.
4. **Run model suggestions** — Click "Run Model Suggestions". Cohere Rerank scores each candidate pair.
5. **Annotate as User A** — Switch to Annotator view. Complete 3 tasks, selecting relevance label and confidence.
6. **Annotate as User B** — Log in as second annotator. Complete the same tasks with different labels to create disagreement.
7. **Review disagreements** — Open Review Queue. Inspect the side-by-side annotations and model suggestion. Submit final reviewer decision.
8. **View metrics** — Open Metrics dashboard. Observe agreement rate, model-human disagreement, and throughput.
9. **Export dataset** — Click "Export", choose JSONL format. Download the file and inspect provenance fields.

## Interview Positioning

> "Based on public evidence, Cohere's Collect team builds internal human-data collection and curation workflows. I built a lower-scale version focused on the same system class: annotation task generation, model-in-the-loop suggestions, consensus, review, dashboards, and export contracts. I used a stack aligned with the Collect posting: Next.js, TypeScript, React, and Python/FastAPI."
