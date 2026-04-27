# Architecture

## System Overview

```
                         ┌────────────────────────────┐
                         │        Next.js App          │
                         │  Admin / Annotator / Review │
                         └─────────────┬──────────────┘
                                       │ REST / JSON
                                       ▼
┌──────────────────────────────────────────────────────────────────┐
│                         FastAPI Backend                          │
│                                                                  │
│  Project API  Dataset API  Task API  Annotation API  Export API  │
│                                                                  │
│  Assignment Engine  Consensus Engine  Model Suggestion Service   │
└──────────────┬───────────────────────┬───────────────────────────┘
               │                       │
               ▼                       ▼
       ┌──────────────┐        ┌────────────────┐
       │ PostgreSQL   │        │ Redis / Queue  │
       │ relational   │        │ async jobs     │
       │ source truth │        └────────────────┘
       └──────────────┘                │
                                       ▼
                         ┌────────────────────────────┐
                         │ Model Providers            │
                         │ Cohere Rerank / Embed      │
                         │ Local fallback models      │
                         └────────────────────────────┘
```

See `system-design.md` for full service breakdown.
