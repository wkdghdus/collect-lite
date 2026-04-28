// Multi-word snake_case keys that should not just title-case via the generic
// rule. Canonical lists live in backend: see app/services/cohere_service.py
// (relevance label vocabulary) and app/models/task.py CHECK constraints
// (task / assignment / consensus statuses).
const OVERRIDES: Record<string, string> = {
  needs_review: "Needs review",
  partially_relevant: "Partially relevant",
  not_relevant: "Not relevant",
  auto_resolved: "Auto-resolved",
  review_resolved: "Review resolved",
};

export function formatStatus(value: string | null | undefined): string {
  if (!value) return "—";
  if (OVERRIDES[value]) return OVERRIDES[value];
  return value.charAt(0).toUpperCase() + value.slice(1).replace(/_/g, " ");
}
