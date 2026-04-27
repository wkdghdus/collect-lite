"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { AppShell } from "@/components/AppShell";
import { MetricsCard } from "@/components/MetricsCard";
import { TaskQueueTable } from "@/components/TaskQueueTable";
import { Button } from "@/components/ui/button";
import type { TaskResponse } from "@/lib/schemas/task";

const inputClass =
  "w-full rounded-md border border-input bg-background px-3 py-2 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring";

export default function TasksPage({ params }: { params: { projectId: string } }) {
  const { projectId } = params;
  const router = useRouter();
  const queryClient = useQueryClient();
  const [templateId, setTemplateId] = useState("");
  const [actionMessage, setActionMessage] = useState<string | null>(null);

  const { data: tasks = [], isLoading, isError, error } = useQuery<TaskResponse[]>({
    queryKey: ["tasks", projectId],
    queryFn: () => api.get<TaskResponse[]>(`/api/projects/${projectId}/tasks`),
  });

  const generate = useMutation({
    mutationFn: (body: { template_id: string; required_annotations: number }) =>
      api.post(`/api/projects/${projectId}/tasks/generate`, body),
    onSuccess: () => {
      setActionMessage("Task generation queued.");
      queryClient.invalidateQueries({ queryKey: ["tasks", projectId] });
    },
    onError: (e) => setActionMessage(e instanceof Error ? e.message : "Generate failed"),
  });

  const suggest = useMutation({
    mutationFn: () => api.post(`/api/projects/${projectId}/tasks/suggest`, {}),
    onSuccess: () => {
      setActionMessage("Model suggestions queued.");
      queryClient.invalidateQueries({ queryKey: ["tasks", projectId] });
    },
    onError: (e) =>
      setActionMessage(
        e instanceof Error ? `Suggestions unavailable: ${e.message}` : "Suggest failed",
      ),
  });

  const counts = {
    created: tasks.filter((t) => t.status === "created").length,
    inProgress: tasks.filter((t) => t.status === "assigned" || t.status === "submitted").length,
    resolved: tasks.filter((t) => t.status === "resolved" || t.status === "exported").length,
  };

  return (
    <AppShell projectId={projectId} section="Tasks">
      <h1 className="text-2xl font-semibold mb-6">Tasks</h1>

      <div className="grid grid-cols-3 gap-4 mb-8">
        <MetricsCard label="Created" value={counts.created} />
        <MetricsCard label="In Progress" value={counts.inProgress} />
        <MetricsCard label="Resolved" value={counts.resolved} />
      </div>

      <div className="rounded-xl border p-4 mb-8 space-y-3">
        <div className="flex flex-wrap items-end gap-3">
          <div className="flex-1 min-w-[260px]">
            <label className="text-sm font-medium block mb-1" htmlFor="template_id">
              Task Template ID
            </label>
            <input
              id="template_id"
              className={inputClass}
              placeholder="UUID of an existing TaskTemplate"
              value={templateId}
              onChange={(e) => setTemplateId(e.target.value)}
            />
          </div>
          <Button
            disabled={!templateId || generate.isPending}
            title={!templateId ? "Enter a TaskTemplate UUID first" : undefined}
            onClick={() =>
              generate.mutate({ template_id: templateId, required_annotations: 2 })
            }
          >
            {generate.isPending ? "Queuing…" : "Generate Tasks"}
          </Button>
          <Button
            variant="outline"
            disabled={suggest.isPending}
            onClick={() => suggest.mutate()}
          >
            {suggest.isPending ? "Queuing…" : "Run Model Suggestions"}
          </Button>
        </div>
        {actionMessage ? (
          <p className="text-sm text-muted-foreground">{actionMessage}</p>
        ) : null}
      </div>

      {isLoading ? (
        <p className="text-muted-foreground">Loading tasks…</p>
      ) : isError ? (
        <p className="text-destructive">
          Failed to load tasks: {error instanceof Error ? error.message : "Unknown error"}
        </p>
      ) : (
        <TaskQueueTable tasks={tasks} onSelect={(id) => router.push(`/tasks/${id}`)} />
      )}
    </AppShell>
  );
}
