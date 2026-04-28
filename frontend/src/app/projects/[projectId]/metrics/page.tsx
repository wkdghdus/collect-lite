"use client";
import { useQuery } from "@tanstack/react-query";
import { AppShell } from "@/components/AppShell";
import { MetricsCard } from "@/components/MetricsCard";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/lib/api";
import type { ProjectMetricsResponse } from "@/lib/schemas/metrics";

const STATUS_FUNNEL: Array<{
  key: keyof Pick<
    ProjectMetricsResponse,
    | "created_count"
    | "suggested_count"
    | "assigned_count"
    | "submitted_count"
    | "needs_review_count"
    | "resolved_count"
    | "exported_count"
  >;
  label: string;
}> = [
  { key: "created_count", label: "Created" },
  { key: "suggested_count", label: "Suggested" },
  { key: "assigned_count", label: "Assigned" },
  { key: "submitted_count", label: "Submitted" },
  { key: "needs_review_count", label: "Needs review" },
  { key: "resolved_count", label: "Resolved" },
  { key: "exported_count", label: "Exported" },
];

function formatPct(value: number | null): string {
  if (value === null) return "—";
  return `${(value * 100).toFixed(1)}%`;
}

export default function MetricsPage({ params }: { params: { projectId: string } }) {
  const { projectId } = params;
  const { data, isLoading, isError, error } = useQuery<ProjectMetricsResponse>({
    queryKey: ["metrics", projectId],
    queryFn: () => api.get<ProjectMetricsResponse>(`/api/projects/${projectId}/metrics`),
  });

  return (
    <AppShell projectId={projectId} section="Metrics">
      <h1 className="mb-6 text-2xl font-semibold">Metrics</h1>
      {isLoading ? (
        <div className="p-12 text-center text-muted-foreground">Loading metrics…</div>
      ) : isError ? (
        <p className="text-destructive">
          Failed to load metrics: {error instanceof Error ? error.message : "Unknown error"}
        </p>
      ) : data ? (
        <div className="space-y-8">
          <section className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <MetricsCard label="Total tasks" value={data.total_tasks} />
            <MetricsCard
              label="Exportable now"
              value={data.exportable_task_count}
              hint="Resolved tasks ready to export"
            />
          </section>

          <section>
            <h2 className="mb-3 text-lg font-medium">Workflow funnel</h2>
            <div className="grid grid-cols-2 gap-3 md:grid-cols-4 lg:grid-cols-7">
              {STATUS_FUNNEL.map(({ key, label }) => (
                <MetricsCard key={key} label={label} value={data[key]} />
              ))}
            </div>
          </section>

          <section>
            <h2 className="mb-3 text-lg font-medium">Quality</h2>
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              <MetricsCard
                label="Average human agreement"
                value={formatPct(data.avg_human_agreement)}
                hint="Mean agreement score across resolved tasks"
              />
              <MetricsCard
                label="Model–human agreement"
                value={formatPct(data.model_human_agreement_rate)}
                hint="Share of tasks where the model's latest suggestion matched the human consensus"
              />
            </div>
          </section>

          <Card>
            <CardHeader>
              <CardTitle>Final label distribution</CardTitle>
            </CardHeader>
            <CardContent>
              <LabelDistribution distribution={data.final_label_distribution} />
            </CardContent>
          </Card>
        </div>
      ) : null}
    </AppShell>
  );
}

function LabelDistribution({ distribution }: { distribution: Record<string, number> }) {
  const entries = Object.entries(distribution).sort(([, a], [, b]) => b - a);
  if (entries.length === 0) {
    return <p className="text-sm text-muted-foreground">No resolved tasks yet.</p>;
  }
  const total = entries.reduce((sum, [, n]) => sum + n, 0);
  return (
    <ul className="space-y-2">
      {entries.map(([label, count]) => {
        const pct = Math.round((count / total) * 100);
        return (
          <li key={label} className="flex items-center justify-between text-sm">
            <span className="font-medium">{label}</span>
            <span className="text-muted-foreground">
              {count} ({pct}%)
            </span>
          </li>
        );
      })}
    </ul>
  );
}
