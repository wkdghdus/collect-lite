"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { AppShell } from "@/components/AppShell";
import { MetricsCard } from "@/components/MetricsCard";
import { TaskQueueTable } from "@/components/TaskQueueTable";
import { Button } from "@/components/ui/button";
import type { TaskResponse, TaskTemplateResponse } from "@/lib/schemas/task";
import type { DatasetResponse } from "@/lib/schemas/dataset";

const inputClass =
  "w-full rounded-md border border-input bg-background px-3 py-2 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring";

export default function TasksPage({ params }: { params: { projectId: string } }) {
  const { projectId } = params;
  const router = useRouter();
  const queryClient = useQueryClient();
  const [templateId, setTemplateId] = useState("");
  const [datasetId, setDatasetId] = useState("");
  const [actionMessage, setActionMessage] = useState<string | null>(null);

  const { data: tasks = [], isLoading, isError, error } = useQuery<TaskResponse[]>({
    queryKey: ["tasks", projectId],
    queryFn: () => api.get<TaskResponse[]>(`/api/projects/${projectId}/tasks`),
  });

  const { data: datasets = [], isLoading: datasetsLoading } = useQuery<DatasetResponse[]>({
    queryKey: ["datasets", projectId],
    queryFn: () => api.get<DatasetResponse[]>(`/api/projects/${projectId}/datasets`),
  });

  const { data: templates = [], isLoading: templatesLoading } = useQuery<
    TaskTemplateResponse[]
  >({
    queryKey: ["templates", projectId],
    queryFn: () =>
      api.get<TaskTemplateResponse[]>(`/api/projects/${projectId}/templates`),
  });

  const generate = useMutation({
    mutationFn: (body: {
      template_id: string;
      dataset_id: string;
      required_annotations: number;
    }) => api.post(`/api/projects/${projectId}/tasks/generate`, body),
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

  const missingSelection =
    !datasetId ? "Select a dataset" : !templateId ? "Select a template" : undefined;

  return (
    <AppShell projectId={projectId} section="Tasks">
      <h1 className="text-2xl font-semibold mb-6">Tasks</h1>

      <div className="grid grid-cols-3 gap-4 mb-8">
        <MetricsCard label="Created" value={counts.created} />
        <MetricsCard label="In Progress" value={counts.inProgress} />
        <MetricsCard label="Resolved" value={counts.resolved} />
      </div>

      <div className="rounded-xl border p-4 mb-8 space-y-3">
        <div className="grid gap-3 md:grid-cols-2">
          <div>
            <label className="text-sm font-medium block mb-1" htmlFor="dataset_id">
              Dataset
            </label>
            <select
              id="dataset_id"
              className={inputClass}
              value={datasetId}
              onChange={(e) => setDatasetId(e.target.value)}
              disabled={datasetsLoading}
            >
              <option value="">
                {datasetsLoading ? "Loading…" : "Select a dataset"}
              </option>
              {datasets.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.filename} ({d.row_count} rows)
                </option>
              ))}
            </select>
            {!datasetsLoading && datasets.length === 0 ? (
              <p className="text-xs text-muted-foreground mt-1">
                No datasets yet —{" "}
                <Link
                  className="underline"
                  href={`/projects/${projectId}/datasets`}
                >
                  upload one first
                </Link>
                .
              </p>
            ) : null}
          </div>
          <div>
            <label className="text-sm font-medium block mb-1" htmlFor="template_id">
              Template
            </label>
            <select
              id="template_id"
              className={inputClass}
              value={templateId}
              onChange={(e) => setTemplateId(e.target.value)}
              disabled={templatesLoading}
            >
              <option value="">
                {templatesLoading ? "Loading…" : "Select a template"}
              </option>
              {templates.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.name}
                </option>
              ))}
            </select>
            {!templatesLoading && templates.length === 0 ? (
              <p className="text-xs text-muted-foreground mt-1">
                No templates yet — recreate the project (rag_relevance auto-seeds one) or
                run <code className="font-mono">python -m scripts.seed</code>.
              </p>
            ) : null}
          </div>
        </div>
        <div className="flex flex-wrap items-end gap-3">
          <Button
            disabled={!templateId || !datasetId || generate.isPending}
            title={missingSelection}
            onClick={() =>
              generate.mutate({
                template_id: templateId,
                dataset_id: datasetId,
                required_annotations: 2,
              })
            }
          >
            {generate.isPending ? "Queuing…" : "Generate Tasks"}
          </Button>
          <Button
            variant="outline"
            disabled
            title="Coming soon — generate suggestions per task from the task detail page."
            onClick={() => suggest.mutate()}
          >
            Run Model Suggestions
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
