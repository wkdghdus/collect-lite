"use client";

import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { AppShell } from "@/components/AppShell";
import { AnnotationCard } from "@/components/AnnotationCard";
import type { TaskResponse } from "@/lib/schemas/task";

export default function TaskWorkbenchPage({ params }: { params: { taskId: string } }) {
  const { taskId } = params;
  const router = useRouter();

  const taskQuery = useQuery<TaskResponse>({
    queryKey: ["task", taskId],
    queryFn: () => api.get<TaskResponse>(`/api/tasks/${taskId}`),
  });

  const task = taskQuery.data;

  async function navigateNext() {
    if (!task) return;
    try {
      const next = await api.get<TaskResponse | null>("/api/tasks/next");
      if (next && next.id !== task.id) {
        router.push(`/tasks/${next.id}`);
      } else {
        router.push(`/projects/${task.project_id}/tasks`);
      }
    } catch {
      router.push(`/projects/${task.project_id}/tasks`);
    }
  }

  async function handleSubmit(label: Record<string, unknown>, confidence: number) {
    if (!task) return;
    try {
      await api.post(`/api/tasks/${task.id}/annotations`, {
        label,
        confidence,
        model_suggestion_visible: false,
      });
    } catch (e) {
      console.error("Submit failed", e);
    }
    await navigateNext();
  }

  async function handleSkip() {
    if (!task) return;
    try {
      await api.post(`/api/tasks/${task.id}/skip`, {});
    } catch (e) {
      console.error("Skip failed", e);
    }
    await navigateNext();
  }

  return (
    <AppShell>
      <h1 className="text-2xl font-semibold mb-6">Annotation Workbench</h1>
      {taskQuery.isLoading ? (
        <p className="text-muted-foreground">Loading task…</p>
      ) : taskQuery.isError ? (
        <p className="text-destructive">
          Failed to load task:{" "}
          {taskQuery.error instanceof Error ? taskQuery.error.message : "Unknown error"}
        </p>
      ) : task ? (
        <AnnotationCard task={task} onSubmit={handleSubmit} onSkip={handleSkip} />
      ) : null}
    </AppShell>
  );
}
