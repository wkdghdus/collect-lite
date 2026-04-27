# frontend/

Next.js 14 App Router + TypeScript. All source lives under `src/`.

## Commands

- **Dev server:** `npm run dev` → http://localhost:3000
- **Production build:** `npm run build`
- **Lint:** `npm run lint`
- **Type-check:** `npx tsc --noEmit`

## Source Layout

- `src/app/` — App Router pages and API routes (see `src/CLAUDE.md`)
- `src/components/` — Feature React components
- `src/components/ui/` — shadcn/ui base components (generated; do not hand-edit)
- `src/lib/` — API client, query client, Zod schemas, utilities

## Key Constraints

- **Path alias:** `@/*` → `src/*` (configured in `tsconfig.json`)
- **Server state:** TanStack Query only — no Redux, no Zustand, no Context for async state
- **Styling:** Tailwind CSS classes + shadcn/ui — no inline `style={{}}` props
- **API calls:** use `src/lib/api.ts` typed client, not raw `fetch`
- **Forms:** react-hook-form + Zod resolver (`@hookform/resolvers/zod`)
