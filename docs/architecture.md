# Architecture

This page is the **one-pager**. For depth, jump to:

- [`architecture/system-design.md`](./architecture/system-design.md) — every runtime component, every wire between them, deployment topology, and an Excalidraw layout guide.
- [`architecture/process-flows.md`](./architecture/process-flows.md) — the eight end-to-end flows, what each one writes/reads, and the task state machine.

## System overview

```
                        ┌────────────────────────────┐
                        │        Next.js App          │
                        │  Admin / Annotator / Review │
                        └─────────────┬──────────────┘
                                      │ REST / JSON
                                      ▼
┌──────────────────────────────────────────────────────────────────┐
│                        FastAPI Backend                           │
│                                                                  │
│  Project · Dataset · Task · Annotation · Suggestion · Consensus  │
│  · Review · Metrics · Export · Users  routers                    │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ In-process BackgroundTasks                                  │  │
│  │ generate_tasks · compute_consensus · create_export          │  │
│  └────────────────────────────────────────────────────────────┘  │
└──────────────┬───────────────────────────────────┬───────────────┘
               │                                   │
        SQL    ▼                       HTTPS       ▼
       ┌──────────────┐         ┌────────────────────────────┐
       │ PostgreSQL   │         │ Cohere Rerank (external)   │
       │ relational   │         │ + local Jaccard fallback   │
       │ source truth │         └────────────────────────────┘
       └──────────────┘
              ▲
              │ DDL on backend boot
       ┌──────────────┐
       │ Alembic      │
       │ migrations   │
       └──────────────┘
```

There is no message broker — async work runs as FastAPI `BackgroundTasks` inside the same process as the API. Export files land on the backend container's local filesystem (currently ephemeral). For details, see the linked docs above.
