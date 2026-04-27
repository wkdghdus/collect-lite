# Evidence and Design Rationale: Lower-Scale Cohere Collect-Inspired System

## Working thesis

Public evidence suggests Cohere's Collect team is a human-data tooling/product team that builds internal tools for collecting, curating, annotating, and evaluating human feedback/data at scale. A lower-scale project should therefore implement a compact internal annotation platform with:

- task/dataset ingestion
- annotator-facing work queues
- model-in-the-loop suggestions
- human feedback collection
- consensus and quality-control workflows
- exportable training/evaluation datasets
- operational dashboards

The project should not claim to replicate Cohere's private internal tooling. It should be framed as a public-evidence-based, lower-scale reconstruction of the likely system class.

## Evidence table

| Evidence | Source | Design implication |
|---|---|---|
| The Software Engineer, Collect role is in Cohere's Inference department and asks for Next.js, TypeScript, React, and Python. | https://jobs.ashbyhq.com/cohere/2786dc50-5662-461a-9946-a821ad42816f | Use Next.js + TypeScript + React for the frontend and Python/FastAPI for backend services. |
| The same Collect SWE role mentions critical internal tools/applications used by hundreds of Cohere employees, snappy web apps, large stakeholder surface area, documentation, and resilient systems. | https://jobs.ashbyhq.com/cohere/2786dc50-5662-461a-9946-a821ad42816f | Build an internal-tool style app: admin/project owner views, annotator views, dashboards, audit logs, and reliability/observability. |
| Product Designer, Human Data postings say the team designs tools and workflows that power human data collection and curation at Cohere, enables high-quality annotation at scale, and works across the full data lifecycle. | https://builtin.com/job/product-designer-human-data/7687345 and https://jobs.entrepreneurs.utoronto.ca/companies/cohere-2-735e1f36-781c-460d-afb7-2515d59858b7/jobs/64536127-product-designer-human-data | Implement dataset lifecycle states: draft, active, annotation, review, exported; include task design/instruction clarity and annotation UX. |
| Product Manager, Human Data postings say human data powers what models learn, improve at, and how they are evaluated, and that the role works across data creation and curation tools/teams. | https://builtin.com/job/product-manager-human-data/6817035 and https://jobs.entrepreneurs.utoronto.ca/companies/cohere-2-9ccb8fa7-ab53-4f10-9eff-0788c149f4e6/jobs/55938847-product-manager-human-data | Include export formats for training/evaluation, task metrics, quality metrics, and model-evaluation datasets. |
| Product Manager and Designer postings reference model-in-the-loop high-quality annotation at enormous scale. | https://builtin.com/job/product-manager-human-data/6817035 and https://jobgether.com/offer/695d2abd2b723d71f726c4fe-product-designer-human-data | Add model-generated suggestions, model confidence, active-learning prioritization, and model-vs-human disagreement review. |
| Cohere Toolkit is a public Cohere repo for building/deploying RAG apps, mostly TypeScript and Python. | https://github.com/cohere-ai/cohere-toolkit | Cohere's public tooling ecosystem supports the same TS/Python full-stack direction. |
| Cohere Toolkit docs say it offers pre-built frontend and backend components for RAG applications. | https://docs.cohere.com/docs/cohere-toolkit | Use modular frontend/backend boundaries and an API-first design. |
| Cohere's public GitHub organization includes Cohere Toolkit, Python SDK, TypeScript SDK, notebooks, and related tooling. | https://github.com/cohere-ai | Use Cohere SDKs where relevant; make the project developer-friendly with docs and seed scripts. |
| Cohere Rerank docs describe reranking as a semantic boost to search quality, useful in RAG and search systems. | https://docs.cohere.com/docs/reranking-with-cohere | Implement a relevance-labeling workflow where Cohere Rerank proposes rankings and humans correct/confirm them. |
| Appen's Cohere case study describes scaling supervised fine-tuning and LLM evaluation with real-time annotation, 2,400+ expert contributor hours, 200 vetted contributors, and a 12-week engagement. | https://www.appen.com/case-studies/cohere-fine-tuning-for-enterprise | Include a realistic "expert annotation" workflow, contributor quality tracking, and preference data export. |

## Recommended lower-scale project scope

Build **CollectLite**, a full-stack human-data collection and evaluation platform for LLM/RAG tasks.

### MVP scope

1. **Project/dataset manager**
   - Create annotation projects.
   - Upload CSV/JSONL datasets.
   - Define task type: pairwise preference, relevance rating, classification, or extraction QA.
   - Write annotation instructions.

2. **Task generation pipeline**
   - Parse uploaded rows.
   - Generate annotation tasks.
   - Optionally run a model-in-the-loop pre-labeling step.
   - Store tasks with priority, confidence, and lifecycle state.

3. **Annotator workbench**
   - Annotator receives assigned tasks.
   - Annotator reads instructions and item context.
   - Annotator labels, ranks, or edits model suggestions.
   - App records time spent, decisions, notes, and confidence.

4. **Quality-control layer**
   - Gold tasks.
   - Multi-annotator consensus.
   - Disagreement queue.
   - Reviewer override.
   - Annotator reliability score.

5. **Model-in-the-loop features**
   - Cohere Rerank or local model ranks candidate documents.
   - Cohere Embed or local embeddings cluster/search items.
   - Optional LLM judge generates draft labels and rationales.
   - Human corrections become training/eval data.

6. **Admin dashboard**
   - Throughput per day.
   - Agreement rate.
   - Model-human disagreement rate.
   - Label distribution.
   - Export readiness.
   - Task latency and completion status.

7. **Dataset export**
   - Export clean JSONL/CSV.
   - Include provenance, annotator ID hash, timestamps, consensus labels, and model suggestion metadata.
   - Support training/evaluation split.

## Why this project fits the interview

This project lets you discuss:

- Next.js, TypeScript, and React via the annotation/admin UI.
- Python/FastAPI via the backend API and model-in-loop services.
- Internal tooling UX, which directly maps to Collect SWE evidence.
- Human data collection/curation, which directly maps to Human Data evidence.
- Model-in-the-loop design, which appears repeatedly in PM/Designer job evidence.
- Production-minded engineering: audit logs, observability, state machines, retryable background jobs, and export contracts.
- Your existing resume strengths: AI ETL pipelines, RAG, Cohere reranking, data validation, observability, stakeholder documentation, and web-app demo experience.

## Caveats

- There is no public GitHub repo for Cohere Collect itself. The system design is inferred from job descriptions, human-data role postings, Cohere public tooling, Cohere docs, and external case-study evidence.
- Avoid saying "this is Cohere's actual Collect architecture." Say: "I designed a lower-scale reconstruction of the system class that Collect appears to own based on public evidence."
