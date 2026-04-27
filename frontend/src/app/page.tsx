"use client";

import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { AppShell } from "@/components/AppShell";
import { ProjectCard } from "@/components/ProjectCard";
import { MetricsCard } from "@/components/MetricsCard";
import { Button } from "@/components/ui/button";
import type { ProjectResponse } from "@/lib/schemas/project";

export default function DashboardPage() {
  const router = useRouter();

  const { data: projects = [], isLoading, isError, error } = useQuery<ProjectResponse[]>({
    queryKey: ["projects"],
    queryFn: () => api.get<ProjectResponse[]>("/api/projects"),
  });

  const counts = {
    total: projects.length,
    active: projects.filter((p) => p.status === "active").length,
    draft: projects.filter((p) => p.status === "draft").length,
  };

  return (
    <AppShell>
      <div className="flex items-center justify-between mb-8">
        <h1 className="text-2xl font-semibold">Dashboard</h1>
        <Button onClick={() => router.push("/projects/new")}>New Project</Button>
      </div>

      <div className="grid grid-cols-3 gap-4 mb-8">
        <MetricsCard label="Projects" value={counts.total} />
        <MetricsCard label="Active" value={counts.active} />
        <MetricsCard label="Draft" value={counts.draft} />
      </div>

      <h2 className="text-lg font-semibold mb-3">Projects</h2>
      {isLoading ? (
        <p className="text-muted-foreground">Loading projects…</p>
      ) : isError ? (
        <p className="text-destructive">
          Failed to load projects: {error instanceof Error ? error.message : "Unknown error"}
        </p>
      ) : projects.length === 0 ? (
        <div className="rounded-xl border p-12 text-center text-muted-foreground">
          No projects yet. Create your first annotation project to get started.
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {projects.map((p) => (
            <ProjectCard
              key={p.id}
              project={p}
              onClick={() => router.push(`/projects/${p.id}`)}
            />
          ))}
        </div>
      )}
    </AppShell>
  );
}
