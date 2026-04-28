"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { AppShell } from "@/components/AppShell";
import { AnnotationCard } from "@/components/AnnotationCard";
import { FlashMessage } from "@/components/FlashMessage";
import { ModelSuggestionPanel } from "@/components/ModelSuggestionPanel";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { formatStatus } from "@/lib/formatStatus";
import type {
  AnnotationSummary,
  ModelSuggestionResponse,
  TaskDetailResponse,
  TaskResponse,
} from "@/lib/schemas/task";
import type { UserResponse } from "@/lib/schemas/user";

const LOCKED_STATUSES = ["needs_review", "resolved", "exported"] as const;
type LockedStatus = (typeof LOCKED_STATUSES)[number];
type AnnotationMode = "create" | "edit" | "locked";

function isLockedStatus(status: string): status is LockedStatus {
  return (LOCKED_STATUSES as readonly string[]).includes(status);
}

export default function TaskWorkbenchPage({ params }: { params: { taskId: string } }) {
  const { taskId } = params;
  const router = useRouter();
  const queryClient = useQueryClient();
  const [flash, setFlash] = useState<string | null>(null);
  const [selectedAnnotatorId, setSelectedAnnotatorId] = useState<string | null>(null);

  const taskQuery = useQuery<TaskDetailResponse>({
    queryKey: ["task", taskId],
    queryFn: () => api.get<TaskDetailResponse>(`/api/tasks/${taskId}`),
  });

  const suggestionsQuery = useQuery<ModelSuggestionResponse[]>({
    queryKey: ["task", taskId, "suggestions"],
    queryFn: () => api.get<ModelSuggestionResponse[]>(`/api/tasks/${taskId}/suggestions`),
  });

  const annotatorsQuery = useQuery<UserResponse[]>({
    queryKey: ["annotators"],
    queryFn: () => api.get<UserResponse[]>("/api/annotators"),
  });

  useEffect(() => {
    if (!selectedAnnotatorId && annotatorsQuery.data && annotatorsQuery.data.length > 0) {
      setSelectedAnnotatorId(annotatorsQuery.data[0].id);
    }
  }, [annotatorsQuery.data, selectedAnnotatorId]);

  const latest = suggestionsQuery.data?.[0] ?? null;

  const generate = useMutation<ModelSuggestionResponse, Error, void>({
    mutationFn: () => api.post<ModelSuggestionResponse>(`/api/tasks/${taskId}/suggestion`, {}),
    onSuccess: () => {
      setFlash("Model suggestion generated.");
      queryClient.invalidateQueries({ queryKey: ["task", taskId, "suggestions"] });
      queryClient.invalidateQueries({ queryKey: ["task", taskId] });
    },
  });

  const task = taskQuery.data;
  const relevance =
    latest && typeof latest.suggestion.relevance === "string"
      ? latest.suggestion.relevance
      : null;

  const myAnnotation: AnnotationSummary | null = useMemo(() => {
    if (!task || !selectedAnnotatorId) return null;
    return task.annotations.find((a) => a.annotator_id === selectedAnnotatorId) ?? null;
  }, [task, selectedAnnotatorId]);

  const taskLocked = !!task && isLockedStatus(task.status);
  const mode: AnnotationMode = myAnnotation
    ? taskLocked
      ? "locked"
      : "edit"
    : "create";

  async function navigateNext() {
    if (!task) return;
    try {
      const params = new URLSearchParams({
        project_id: task.project_id,
        exclude_task_id: task.id,
      });
      if (selectedAnnotatorId) params.set("annotator_id", selectedAnnotatorId);
      const next = await api.get<TaskResponse | null>(
        `/api/tasks/next?${params.toString()}`,
      );
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
    if (!selectedAnnotatorId) {
      setFlash("Choose an annotator before submitting.");
      return;
    }
    try {
      if (mode === "edit" && myAnnotation) {
        await api.patch(`/api/tasks/${task.id}/annotations/${myAnnotation.id}`, {
          annotator_id: selectedAnnotatorId,
          label,
          confidence,
          model_suggestion_visible: latest != null,
        });
        setFlash("Annotation updated.");
        queryClient.invalidateQueries({ queryKey: ["task", taskId] });
        queryClient.invalidateQueries({ queryKey: ["tasks", task.project_id] });
        return;
      }
      await api.post(`/api/tasks/${task.id}/annotations`, {
        annotator_id: selectedAnnotatorId,
        label,
        confidence,
        model_suggestion_visible: latest != null,
      });
      setFlash("Annotation submitted.");
      queryClient.invalidateQueries({ queryKey: ["task", taskId] });
      queryClient.invalidateQueries({ queryKey: ["tasks", task.project_id] });
      // Hold the flash on-screen briefly before routing to the next task.
      await new Promise((r) => setTimeout(r, 600));
    } catch (e) {
      console.error("Submit failed", e);
      setFlash("Submit failed — see console for details.");
      return;
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

  const projectTaskType = "rag_relevance";
  const banner =
    mode === "edit" ? (
      <div
        role="status"
        className="rounded-md border border-primary/40 bg-primary/10 px-4 py-3 text-sm"
      >
        You have already annotated this task — editing your submission.
      </div>
    ) : mode === "locked" && task ? (
      <div
        role="status"
        className="rounded-md border border-muted-foreground/30 bg-muted/40 px-4 py-3 text-sm"
      >
        Annotation locked — task is {formatStatus(task.status)}.
      </div>
    ) : null;

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
        <FlashMessage message={flash} onDismiss={() => setFlash(null)} />
      </section>

      <section className="mb-4 flex items-center gap-3">
        <label htmlFor="annotator-switcher" className="text-sm font-medium">
          Acting as:
        </label>
        <select
          id="annotator-switcher"
          className="h-9 rounded-md border bg-background px-3 text-sm"
          value={selectedAnnotatorId ?? ""}
          onChange={(e) => setSelectedAnnotatorId(e.target.value)}
          disabled={annotatorsQuery.isLoading || !annotatorsQuery.data?.length}
        >
          {annotatorsQuery.data?.map((u) => (
            <option key={u.id} value={u.id}>
              {u.name} ({u.email})
            </option>
          )) ?? null}
        </select>
        {annotatorsQuery.isError ? (
          <span className="text-xs text-destructive">Failed to load annotators</span>
        ) : null}
      </section>

      {banner ? <div className="mb-4">{banner}</div> : null}

      {taskQuery.isLoading ? (
        <p className="text-muted-foreground">Loading task…</p>
      ) : taskQuery.isError ? (
        <p className="text-destructive">
          Failed to load task:{" "}
          {taskQuery.error instanceof Error ? taskQuery.error.message : "Unknown error"}
        </p>
      ) : task ? (
        <AnnotationCard
          task={task}
          taskType={projectTaskType}
          onSubmit={handleSubmit}
          onSkip={handleSkip}
          submitDisabled={!selectedAnnotatorId}
          mode={mode}
          existingAnnotation={myAnnotation}
        />
      ) : null}
    </AppShell>
  );
}
