# frontend/src/

## App Router Pages (`app/`)

| Route | File | Purpose |
|-------|------|---------|
| `/` | `app/page.tsx` | Dashboard — project counts + grid + new-project entry |
| `/projects` | `app/projects/page.tsx` | Project list + create |
| `/projects/new` | `app/projects/new/page.tsx` | Create-project form (react-hook-form + Zod) |
| `/projects/[projectId]` | `app/projects/[projectId]/page.tsx` | Project detail + section nav |
| `/projects/[projectId]/datasets` | `.../datasets/page.tsx` | Dataset upload + list |
| `/projects/[projectId]/tasks` | `.../tasks/page.tsx` | Task queue + Generate Tasks form. Renders Dataset and Template `<select>` dropdowns populated from `GET /api/projects/{id}/datasets` and `GET /api/projects/{id}/templates`; `POST /api/projects/{id}/tasks/generate` body is `{template_id, dataset_id, required_annotations: 2}`. Empty-list hints link out to the datasets page or instruct re-seeding. The legacy `Run Model Suggestions` batch button stays disabled — generate suggestions per task from the task detail page |
| `/projects/[projectId]/review` | `.../review/page.tsx` | Reviewer queue — fetches `GET /api/projects/{id}/review/tasks`; submits decisions via `POST /api/tasks/{taskId}/review` and invalidates the queue query so resolved tasks drop off |
| `/projects/[projectId]/metrics` | `.../metrics/page.tsx` | Project metrics dashboard — fetches `GET /api/projects/{id}/metrics`. Renders four sections: hero (`total_tasks` + `exportable_task_count`), workflow funnel (`MetricsCard` per status in `created → suggested → assigned → submitted → needs_review → resolved → exported` order), quality (`avg_human_agreement` + `model_human_agreement_rate` as percents, em-dash when `null`), and a `final_label_distribution` card listing each label with count + percent of total |
| `/projects/[projectId]/exports` | `.../exports/page.tsx` | Per-project exports page — fetches `GET /api/projects/{id}/exports` for the persisted list (newest-first, polls every 2s while any row is non-terminal), POSTs `/api/projects/{id}/exports` from one of two buttons (Generate JSONL / Generate CSV) and invalidates the list query on success, downloads via `GET /api/exports/{id}/download` |
| `/tasks/[taskId]` | `app/tasks/[taskId]/page.tsx` | Annotation workbench — fetches `GET /api/tasks/{task_id}` as a `TaskDetailResponse` (so `query` and `candidate_document` are rendered as labelled blocks instead of a JSON dump), `GET /api/tasks/{task_id}/suggestions`, and `GET /api/annotators`. Renders an "Acting as:" `<select>` populated from the annotators query (defaults to the first row); the chosen `annotator_id` is sent on every annotation submit, so the backend lazily resolves or creates an `Assignment`. Submit posts `{annotator_id, label, confidence, model_suggestion_visible}` and invalidates `["task", taskId]` + `["tasks", task.project_id]` so the queue's `annotation_count` badge updates without a hard reload |
| `api/auth/[...nextauth]` | `app/api/auth/.../route.ts` | NextAuth credentials handler |

Shared: `app/layout.tsx` (root layout + Providers), `app/providers.tsx` (QueryClientProvider)

## Feature Components (`components/`)

`AppShell` · `ProjectCard` · `DatasetUploader` · `TaskQueueTable` · `AnnotationCard`
`AnnotationWorkbench` · `ModelSuggestionPanel` · `ReviewQueueItemCard`
`MetricsCard` · `ConsensusBadge` · `TaskTemplateEditor` · `FlashMessage`

`AnnotationCard` accepts a `taskType` prop. When `taskType === 'rag_relevance'` it
renders a fieldset of three radio buttons (`relevant` / `partially_relevant` /
`not_relevant`) and disables Submit until one is picked. When the task object is a
`TaskDetailResponse`, the card replaces the legacy JSON dump with two labelled
blocks ("Query" and "Candidate document") sourced from the embedded payload.

`FlashMessage` is a small auto-dismissing inline banner used for one-shot success
confirmations after mutations (annotation submit, suggestion generate, review
submit, export create). Each consuming page owns a local `useState<string | null>`
and clears it via the `onDismiss` callback after `durationMs` (default 3000).

## Lib (`lib/`)

- `api.ts` — typed `get`/`post`/`patch` wrappers (uses `NEXT_PUBLIC_API_URL`)
- `queryClient.ts` — TanStack QueryClient singleton (30s staleTime)
- `utils.ts` — `cn()` helper (clsx + tailwind-merge)
- `formatStatus.ts` — `formatStatus(value)` returns a human-readable label for backend status strings (`needs_review` → "Needs review", `partially_relevant` → "Partially relevant"). Use it on every JSX render of a backend status field; canonical vocabulary lives in `backend/app/services/cohere_service.py` and the `Task`/`Assignment`/`ConsensusResult` CHECK constraints.
- `schemas/` — Zod schemas mirroring backend Pydantic models: `project`, `dataset`, `task`, `annotation`, `export`, `review`, `metrics`
