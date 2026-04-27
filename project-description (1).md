---
title: CollectLite
startDate: 2026-04
endDate: 2026-04
organization: Personal Project
description: A lower-scale human-data collection and model-evaluation platform inspired by public evidence about Cohere's Collect / Human Data tooling. The system lets project owners upload datasets, create annotation tasks, use model-in-the-loop suggestions, collect human feedback, resolve disagreement, monitor data quality, and export training/evaluation-ready datasets.
githubUrl: https://github.com/wkdghdus/collect-lite
tags: [full-stack, internal-tools, human-data, annotation-platform, model-evaluation, llmops, nextjs, typescript, react, fastapi, python, postgres, cohere, docker]
# coverImage: assets/collect-lite-preview.jpg
---

## Overview

CollectLite is a full-stack human-data collection and model-evaluation platform designed as a lower-scale reconstruction of the kind of system Cohere's Collect team appears to build publicly: internal tools and workflows for human data collection, annotation, curation, and model evaluation.

The system supports project owners who need to turn raw examples into high-quality model training or evaluation datasets. Users can create annotation projects, upload CSV or JSONL files, define task instructions, generate annotation queues, run model-in-the-loop pre-labeling, collect human feedback, measure agreement, resolve disagreements, and export clean datasets for downstream training or evaluation.

The project was intentionally scoped around Cohere's public Collect and Human Data evidence. Public job postings describe Collect engineers as working on critical internal tools with Next.js, TypeScript, React, and Python, while Human Data postings describe tools and workflows for annotation, data curation, model-in-the-loop labeling, and evaluation. CollectLite implements those ideas at a personal-project scale.

## Problem

High-quality human data is one of the hardest parts of building reliable AI systems. Raw datasets often lack clear labels, inconsistent instructions create noisy annotations, and model outputs need structured human review before they can be used for training or evaluation.

The core problems CollectLite addresses are:

1. **Annotation workflow fragmentation** — teams often manage task instructions, raw data, assignments, review, and exports across disconnected spreadsheets and scripts.
2. **Inconsistent label quality** — labels need consensus, reviewer override, gold examples, and disagreement tracking to become trustworthy training/evaluation data.
3. **Model-in-the-loop complexity** — model suggestions can speed up annotation, but they must be stored with provenance and compared against human decisions.
4. **Export reliability** — downstream training and evaluation pipelines need schema-consistent, auditable JSONL/CSV outputs.
5. **Internal-tool usability** — annotators need a fast, clear UI, while project owners need dashboards for progress, quality, and bottlenecks.

## My Role

I designed and implemented CollectLite as a full-stack SWE/AI systems project. My work included:

- Researching public evidence about Cohere's Collect and Human Data teams.
- Designing a lower-scale architecture that maps to Collect-like internal tooling.
- Building a Next.js + TypeScript annotator/admin interface.
- Implementing a Python FastAPI backend with project, task, assignment, annotation, review, and export APIs.
- Designing a relational Postgres schema for annotation lifecycle state, consensus labels, model suggestions, audit logs, and dataset exports.
- Adding model-in-the-loop pre-labeling using Cohere Rerank/Embed or local fallback models.
- Implementing consensus, disagreement queues, gold-task checks, and reviewer override workflows.
- Building operational dashboards for throughput, agreement, label distribution, model-human disagreement, and export readiness.
- Containerizing the stack with Docker Compose and documenting setup, API contracts, and system design.

## System Architecture

At a high level, the system follows this flow:

```text
Dataset upload
        ↓
Schema validation and row normalization
        ↓
Task generation
        ↓
Model-in-the-loop suggestions
        ↓
Annotator work queue
        ↓
Human annotation capture
        ↓
Consensus and quality-control engine
        ↓
Reviewer disagreement resolution
        ↓
Dataset export
        ↓
Training / evaluation-ready JSONL or CSV
```

The platform separates user-facing workflows from backend data contracts. The frontend handles project management, annotation workbench, review queues, and dashboards. The backend owns lifecycle state, validation, assignment logic, model suggestion generation, consensus computation, audit logging, and export generation.

## Core Product Surfaces

### Project Owner Dashboard

Project owners can create annotation projects, upload raw examples, define task types, write labeling instructions, monitor task progress, inspect quality metrics, and export datasets.

Supported task types:

- Pairwise preference ranking
- Document relevance rating
- Classification
- Extraction/QA validation
- Freeform model response critique

### Dataset Upload and Validation

Users upload CSV or JSONL files. The backend validates required fields, normalizes row IDs, detects duplicates, and creates immutable source examples.

Example dataset row:

```json
{
  "query": "What documents are needed for mortgage renewal?",
  "candidate_a": "Income verification and property tax documents...",
  "candidate_b": "A branch address and appointment confirmation...",
  "metadata": {"domain": "banking", "source": "demo"}
}
```

Each uploaded row receives a canonical `example_id`, source hash, project ID, and ingestion timestamp.

### Task Generation

The task generator converts source rows into annotation tasks. Each task stores:

- project ID
- example ID
- task type
- instruction version
- priority
- model suggestion status
- assignment state
- lifecycle status

Task states:

```text
created → suggested → assigned → submitted → needs_review → resolved → exported
```

### Model-in-the-Loop Suggestions

Before humans annotate, the system can call a model-assisted pre-labeling pipeline.

For relevance or RAG-style tasks, Cohere Rerank can score candidate documents against a query. For classification or critique tasks, an LLM can draft a suggested label and short rationale. These suggestions are shown to annotators as optional assistance, not treated as ground truth.

Stored model suggestion metadata includes:

- model provider
- model name
- prompt/template version
- raw score or label
- rationale
- confidence
- created timestamp
- latency and cost estimate

This allows the dashboard to compare model suggestions against human consensus later.

### Annotator Workbench

Annotators receive tasks from an assignment queue. The UI emphasizes speed and clarity:

- task instructions pinned at the top
- item context in the center
- candidate responses/documents side by side
- model suggestion panel
- label controls
- confidence selector
- optional notes
- submit and skip actions

The system records annotation latency, selected labels, confidence, notes, model-suggestion visibility, and assignment metadata.

### Consensus and Quality Control

CollectLite supports multiple quality-control mechanisms:

1. **Multi-annotator consensus** — assign the same task to multiple annotators and compute agreement.
2. **Gold tasks** — insert known-answer tasks to estimate annotator reliability.
3. **Disagreement queue** — send low-agreement tasks to reviewer resolution.
4. **Reviewer override** — allow senior reviewers to set final labels.
5. **Model-human disagreement** — flag cases where model suggestions disagree with consensus.

Consensus outputs are stored separately from raw annotations so the platform preserves both individual labels and final resolved labels.

### Review Queue

Reviewers see tasks that require adjudication. A task enters review when:

- annotators disagree beyond a threshold
- annotator confidence is low
- model and human labels strongly disagree
- the task is a gold-task failure
- a project owner manually flags it

The reviewer can inspect all raw annotations, comments, model suggestions, and source metadata before resolving the final label.

### Export Pipeline

The export service generates clean JSONL or CSV files for training and evaluation.

Export records include:

- example ID
- source fields
- final label
- consensus score
- number of annotations
- reviewer override flag
- model suggestion metadata
- instruction version
- split assignment: train, validation, or evaluation
- provenance timestamps

This makes the output usable for supervised fine-tuning, model evaluation, reranker evaluation, or RAG-quality benchmarking.

## Data Model

Core tables:

- `users`
- `projects`
- `datasets`
- `source_examples`
- `task_templates`
- `tasks`
- `assignments`
- `annotations`
- `model_suggestions`
- `consensus_results`
- `review_decisions`
- `gold_labels`
- `exports`
- `audit_events`

The schema is designed around immutability where possible. Raw examples, annotation submissions, model suggestions, and audit events are append-only. Resolved consensus and export records are versioned.

## API Design

Representative endpoints:

```text
POST   /api/projects
GET    /api/projects
POST   /api/projects/{project_id}/datasets
POST   /api/projects/{project_id}/tasks/generate
POST   /api/projects/{project_id}/tasks/suggest
GET    /api/tasks/next
POST   /api/tasks/{task_id}/annotations
GET    /api/projects/{project_id}/review-queue
POST   /api/reviews/{task_id}/resolve
GET    /api/projects/{project_id}/metrics
POST   /api/projects/{project_id}/exports
GET    /api/exports/{export_id}/download
```

The backend exposes typed OpenAPI documentation through FastAPI, and the frontend uses generated TypeScript API types to reduce frontend/backend drift.

## Observability and Reliability

The project includes lightweight production-minded instrumentation:

- structured JSON logs
- request latency middleware
- background job status tracking
- task lifecycle counters
- failed model-call retries
- export audit records
- dashboard metrics

Main operational metrics:

- tasks created
- tasks completed
- average annotation latency
- consensus agreement rate
- gold-task accuracy
- model-human disagreement rate
- review backlog
- export readiness

## Technology Stack

### Frontend

- Next.js
- TypeScript
- React
- Tailwind CSS
- shadcn/ui
- TanStack Query
- Recharts

### Backend

- Python
- FastAPI
- Pydantic
- SQLAlchemy
- Alembic
- PostgreSQL
- Redis Queue or FastAPI background tasks

### AI / Model-in-the-Loop

- Cohere Rerank for relevance-ranking tasks
- Cohere Embed for semantic similarity and clustering
- Optional local fallback with SentenceTransformers
- Optional LLM judge for draft labels and rationales

### DevOps

- Docker Compose
- GitHub Actions
- pytest
- Playwright or React Testing Library
- Ruff / Black
- ESLint / Prettier

## Lower-Scale Implementation Plan

### Day 1: Core CRUD and upload

- Create repo and Docker Compose stack.
- Implement Postgres schema and Alembic migrations.
- Build project creation and dataset upload.
- Add row validation and source-example creation.
- Build simple admin dashboard.

### Day 2: Annotation flow

- Generate tasks from uploaded rows.
- Build annotator queue and task workbench.
- Implement annotation submission.
- Add assignment and task-state transitions.
- Seed demo users and demo dataset.

### Day 3: Model-in-the-loop and quality

- Add Cohere Rerank or local reranker suggestions.
- Store model suggestion metadata.
- Compute consensus from multiple annotations.
- Build disagreement review queue.
- Add gold-task reliability scoring.

### Day 4: Dashboard and export

- Build metrics dashboard.
- Add JSONL/CSV export pipeline.
- Add audit logs.
- Polish README, architecture diagram, screenshots, and demo script.

## Demo Scenario

The demo project uses a RAG relevance-labeling workflow.

1. Upload a dataset of user queries and candidate retrieved documents.
2. Generate relevance-labeling tasks.
3. Run Cohere Rerank to pre-score each candidate document.
4. Annotators label each candidate as irrelevant, partially relevant, or highly relevant.
5. The system computes consensus and flags disagreements.
6. Reviewers resolve ambiguous cases.
7. Project owner exports a clean reranker-evaluation dataset.
8. Dashboard shows throughput, agreement, and model-human disagreement.

## Scale

CollectLite is intentionally lower-scale but production-shaped.

Target local/demo scale:

- 1-5 projects
- 100-5,000 source examples
- 500-25,000 generated tasks
- 2-10 annotator accounts
- 2-3 annotations per task
- JSONL/CSV exports up to tens of thousands of records

## Results Summary

The intended result is a polished interview project that demonstrates full-stack engineering, AI systems thinking, and internal-tool product judgment.

Expected outcomes:

- End-to-end annotation workflow from dataset upload to export.
- Model-in-the-loop suggestions stored with provenance.
- Consensus and disagreement resolution workflow.
- Dashboard for data quality and project progress.
- Exportable training/evaluation dataset.
- Clear documentation and system design artifacts.

## Technical Highlights

### Internal Tooling UX

The platform is designed for two user types: project owners and annotators. Project owners need operational visibility; annotators need a fast and unambiguous labeling interface.

### Model-in-the-Loop Annotation

Model suggestions are used to accelerate human labeling while preserving human decisions as the source of truth. The system explicitly tracks disagreement between model suggestions and human consensus.

### Annotation Quality Control

Consensus, gold tasks, reviewer overrides, and annotator reliability scores turn raw labels into trusted data.

### Export Contracts

Exports are schema-controlled and include provenance fields, making the generated data suitable for model evaluation or fine-tuning.

### Production-Minded Design

Even at small scale, the system includes state machines, audit logs, background jobs, typed APIs, schema migrations, and observability metrics.

## Challenges

### Scope Management

The biggest challenge is keeping the system buildable before the interview. The MVP focuses on one strong workflow: RAG relevance labeling with optional pairwise preference ranking.

### Annotation UX

Small UI choices affect label quality. Instructions, candidate layout, keyboard shortcuts, and confidence controls need to be simple and fast.

### Model Suggestion Bias

Showing model suggestions can bias human annotators. CollectLite logs whether suggestions were visible and can support an ablation mode where some tasks hide suggestions.

### Consensus Design

Consensus is straightforward for classification but harder for ranking and freeform critique. The MVP starts with majority vote and reviewer override.

### Export Correctness

Training/evaluation exports must avoid schema drift. The system version-controls instruction templates and export schemas.

## What I Learned

This project demonstrates that human-data platforms are not just labeling UIs. They require careful system design around workflow state, data quality, model assistance, provenance, auditability, and downstream training/evaluation contracts.

It also helped connect my existing AI/data engineering background to full-stack product engineering. I designed a system that combines frontend UX, backend APIs, data modeling, AI services, quality metrics, and production-style observability.

## Technologies Used

- Next.js
- TypeScript
- React
- Tailwind CSS
- shadcn/ui
- TanStack Query
- Recharts
- Python
- FastAPI
- Pydantic
- SQLAlchemy
- Alembic
- PostgreSQL
- Redis Queue / background jobs
- Cohere Rerank
- Cohere Embed
- SentenceTransformers
- Docker Compose
- GitHub Actions
- pytest
- Playwright / React Testing Library
- JSONL / CSV exports

## Future Improvements

- Add organization-level role-based access control.
- Add keyboard-first annotator shortcuts.
- Add active-learning prioritization using model uncertainty.
- Add pairwise Bradley-Terry aggregation for preference ranking.
- Add prompt/version registry for model suggestions.
- Add blind annotation mode to reduce model-suggestion bias.
- Add webhook export to training pipelines.
- Add OpenTelemetry tracing and Prometheus metrics.
- Add dataset diffing between export versions.
- Add multi-tenant project isolation.
