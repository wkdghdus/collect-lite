"use client";

import { useRouter } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { AppShell } from "@/components/AppShell";
import { AnnotationCard } from "@/components/AnnotationCard";
import { ModelSuggestionPanel } from "@/components/ModelSuggestionPanel";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { ModelSuggestionResponse, TaskResponse } from "@/lib/schemas/task";

export default function TaskWorkbenchPage({ params }: { params: { taskId: string } }) {
  const { taskId } = params;
  const router = useRouter();
  const queryClient = useQueryClient();

  const taskQuery = useQuery<TaskResponse>({
    queryKey: ["task", taskId],
    queryFn: () => api.get<TaskResponse>(`/api/tasks/${taskId}`),
  });

  const suggestionsQuery = useQuery<ModelSuggestionResponse[]>({
    queryKey: ["task", taskId, "suggestions"],
    queryFn: () => api.get<ModelSuggestionResponse[]>(`/api/tasks/${taskId}/suggestions`),
  });

  const latest = suggestionsQuery.data?.[0] ?? null;

  const generate = useMutation<ModelSuggestionResponse, Error, void>({
    mutationFn: () => api.post<ModelSuggestionResponse>(`/api/tasks/${taskId}/suggestion`, {}),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["task", taskId, "suggestions"] });
      queryClient.invalidateQueries({ queryKey: ["task", taskId] });
    },
  });

  const task = taskQuery.data;
  const relevance =
    latest && typeof latest.suggestion.relevance === "string"
      ? latest.suggestion.relevance
      : null;

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
        model_suggestion_visible: latest != null,
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

      <section className="space-y-3 mb-6">
        <ModelSuggestionPanel suggestion={latest} />
        {relevance ? (
          <Badge variant="secondary">Suggested label: {relevance}</Badge>
        ) : null}
        <div className="flex items-center gap-3">
          <Button
            variant="outline"
            onClick={() => generate.mutate()}
            disabled={generate.isPending}
          >
            {generate.isPending ? "Generating…" : "Generate model suggestion"}
          </Button>
          {generate.isError ? (
            <p className="text-sm text-destructive">
              Failed to generate suggestion: {generate.error.message}
            </p>
          ) : null}
        </div>
      </section>

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
