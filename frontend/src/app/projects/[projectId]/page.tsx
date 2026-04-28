"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { AppShell } from "@/components/AppShell";
import { MetricsCard } from "@/components/MetricsCard";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardTitle } from "@/components/ui/card";
import { formatStatus } from "@/lib/formatStatus";
import type { ProjectResponse } from "@/lib/schemas/project";
import type { ProjectMetricsResponse } from "@/lib/schemas/metrics";

const SECTIONS = [
  { slug: "datasets", title: "Datasets", desc: "Upload CSV / JSONL data" },
  { slug: "tasks", title: "Tasks", desc: "Generate and run task queue" },
  { slug: "review", title: "Review", desc: "Resolve disagreements" },
  { slug: "metrics", title: "Metrics", desc: "Workflow funnel + agreement" },
  { slug: "exports", title: "Exports", desc: "Create and download exports" },
];

export default function ProjectDetailPage({ params }: { params: { projectId: string } }) {
  const { projectId } = params;

  const projectQuery = useQuery<ProjectResponse>({
    queryKey: ["projects", projectId],
    queryFn: () => api.get<ProjectResponse>(`/api/projects/${projectId}`),
  });

  const metricsQuery = useQuery<ProjectMetricsResponse>({
    queryKey: ["metrics", projectId],
    queryFn: () => api.get<ProjectMetricsResponse>(`/api/projects/${projectId}/metrics`),
    retry: false,
  });

  const project = projectQuery.data;
  const metrics = metricsQuery.data;
  const resolvedPct =
    metrics && metrics.total_tasks > 0
      ? `${((metrics.resolved_count / metrics.total_tasks) * 100).toFixed(0)}%`
      : "—";

  return (
    <AppShell projectId={projectId} section="Overview">
      {projectQuery.isLoading ? (
        <p className="text-muted-foreground">Loading project…</p>
      ) : projectQuery.isError ? (
        <p className="text-destructive">Failed to load project.</p>
      ) : project ? (
        <>
          <div className="flex items-center justify-between mb-2">
            <h1 className="text-2xl font-semibold">{project.name}</h1>
            <Badge>{formatStatus(project.status)}</Badge>
          </div>
          <p className="text-sm text-muted-foreground mb-8">{project.task_type}</p>

          <div className="grid grid-cols-3 gap-4 mb-8">
            <MetricsCard label="Tasks Total" value={metrics?.total_tasks ?? "—"} />
            <MetricsCard label="Pending Review" value={metrics?.needs_review_count ?? "—"} />
            <MetricsCard label="Resolved" value={resolvedPct} />
          </div>

          <h2 className="text-lg font-semibold mb-3">Sections</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {SECTIONS.map((s) => (
              <Link key={s.slug} href={`/projects/${projectId}/${s.slug}`}>
                <Card className="cursor-pointer hover:shadow-md transition-shadow">
                  <CardContent className="p-6">
                    <CardTitle className="text-base mb-1">{s.title}</CardTitle>
                    <p className="text-sm text-muted-foreground">{s.desc}</p>
                  </CardContent>
                </Card>
              </Link>
            ))}
          </div>
        </>
      ) : null}
    </AppShell>
  );
}
