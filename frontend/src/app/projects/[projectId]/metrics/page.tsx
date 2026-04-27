"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { AppShell } from "@/components/AppShell";
import { MetricsDashboard } from "@/components/MetricsDashboard";

interface ProjectMetrics {
  tasks_total: number;
  tasks_resolved: number;
  review_backlog: number;
  agreement_rate: number;
  gold_accuracy: number;
  model_human_disagreement_rate: number;
  avg_annotation_latency_ms: number;
}

export default function MetricsPage({ params }: { params: { projectId: string } }) {
  const { projectId } = params;

  const { data, isLoading, isError, error } = useQuery<ProjectMetrics>({
    queryKey: ["metrics", projectId],
    queryFn: () => api.get<ProjectMetrics>(`/api/projects/${projectId}/metrics`),
    retry: false,
  });

  return (
    <AppShell projectId={projectId} section="Metrics">
      <h1 className="text-2xl font-semibold mb-6">Metrics</h1>
      {isLoading ? (
        <div className="text-center text-muted-foreground p-12">Loading metrics…</div>
      ) : isError ? (
        <p className="text-destructive">
          Failed to load metrics: {error instanceof Error ? error.message : "Unknown error"}
        </p>
      ) : (
        <MetricsDashboard metrics={data ?? null} />
      )}
    </AppShell>
  );
}
