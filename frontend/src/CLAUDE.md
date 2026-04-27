# frontend/src/

## App Router Pages (`app/`)

| Route | File | Purpose |
|-------|------|---------|
| `/` | `app/page.tsx` | Redirects to `/projects` |
| `/projects` | `app/projects/page.tsx` | Project list + create |
| `/projects/[projectId]` | `app/projects/[projectId]/page.tsx` | Project detail + nav |
| `/projects/[projectId]/datasets` | `.../datasets/page.tsx` | Dataset upload + validation |
| `/projects/[projectId]/tasks` | `.../tasks/page.tsx` | Task generation + model suggestions |
| `/projects/[projectId]/review` | `.../review/page.tsx` | Reviewer disagreement queue |
| `/projects/[projectId]/metrics` | `.../metrics/page.tsx` | Dashboard charts |
| `/annotate` | `app/annotate/page.tsx` | Annotator workbench |
| `/exports` | `app/exports/page.tsx` | Export management |
| `api/auth/[...nextauth]` | `app/api/auth/.../route.ts` | NextAuth credentials handler |

Shared: `app/layout.tsx` (root layout + Providers), `app/providers.tsx` (QueryClientProvider)

## Feature Components (`components/`)

`ProjectCard` · `DatasetUploader` · `AnnotationWorkbench` · `ModelSuggestionPanel`
`ReviewQueueTable` · `MetricsDashboard` · `ExportBuilder` · `ConsensusBadge` · `TaskTemplateEditor`

## Lib (`lib/`)

- `api.ts` — typed `get`/`post`/`patch` wrappers (uses `NEXT_PUBLIC_API_URL`)
- `queryClient.ts` — TanStack QueryClient singleton (30s staleTime)
- `utils.ts` — `cn()` helper (clsx + tailwind-merge)
- `schemas/` — Zod schemas mirroring backend Pydantic models: `project`, `dataset`, `task`, `annotation`, `export`
