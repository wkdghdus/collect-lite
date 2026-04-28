# frontend/src/

## App Router Pages (`app/`)

| Route | File | Purpose |
|-------|------|---------|
| `/` | `app/page.tsx` | Dashboard — project counts + grid + new-project entry |
| `/projects` | `app/projects/page.tsx` | Project list + create |
| `/projects/new` | `app/projects/new/page.tsx` | Create-project form (react-hook-form + Zod) |
| `/projects/[projectId]` | `app/projects/[projectId]/page.tsx` | Project detail + section nav |
| `/projects/[projectId]/datasets` | `.../datasets/page.tsx` | Dataset upload + list |
| `/projects/[projectId]/tasks` | `.../tasks/page.tsx` | Task queue, generate, suggestions |
| `/projects/[projectId]/review` | `.../review/page.tsx` | Reviewer queue — fetches `GET /api/projects/{id}/review/tasks`; submits decisions via `POST /api/tasks/{taskId}/review` and invalidates the queue query so resolved tasks drop off |
| `/projects/[projectId]/metrics` | `.../metrics/page.tsx` | Project metrics tiles |
| `/projects/[projectId]/exports` | `.../exports/page.tsx` | Per-project exports page — fetches `GET /api/projects/{id}/exports` for the persisted list (newest-first, polls every 2s while any row is non-terminal), POSTs `/api/projects/{id}/exports` from one of two buttons (Generate JSONL / Generate CSV) and invalidates the list query on success, downloads via `GET /api/exports/{id}/download` |
| `/tasks/[taskId]` | `app/tasks/[taskId]/page.tsx` | Annotation workbench — also fetches `GET /api/tasks/{task_id}/suggestions` and posts `POST /api/tasks/{task_id}/suggestion` to render/generate model suggestions via `ModelSuggestionPanel` |
| `/annotate` | `app/annotate/page.tsx` | Legacy global annotator workbench (kept untouched; superseded by `/tasks/[taskId]`) |
| `/exports` | `app/exports/page.tsx` | Legacy global exports page (kept untouched; superseded by `/projects/[projectId]/exports`) |
| `api/auth/[...nextauth]` | `app/api/auth/.../route.ts` | NextAuth credentials handler |

Shared: `app/layout.tsx` (root layout + Providers), `app/providers.tsx` (QueryClientProvider)

## Feature Components (`components/`)

`AppShell` · `ProjectCard` · `DatasetUploader` · `TaskQueueTable` · `AnnotationCard`
`AnnotationWorkbench` · `ModelSuggestionPanel` · `ReviewQueueItemCard`
`MetricsCard` · `MetricsDashboard` · `ConsensusBadge` · `TaskTemplateEditor`

## Lib (`lib/`)

- `api.ts` — typed `get`/`post`/`patch` wrappers (uses `NEXT_PUBLIC_API_URL`)
- `queryClient.ts` — TanStack QueryClient singleton (30s staleTime)
- `utils.ts` — `cn()` helper (clsx + tailwind-merge)
- `schemas/` — Zod schemas mirroring backend Pydantic models: `project`, `dataset`, `task`, `annotation`, `export`, `review`
