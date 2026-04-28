"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { AppShell } from "@/components/AppShell";
import { FlashMessage } from "@/components/FlashMessage";
import { ReviewQueueItemCard } from "@/components/ReviewQueueItemCard";
import { api } from "@/lib/api";
import type {
  ReviewDecisionCreate,
  ReviewQueueItem,
  ReviewSubmitResponse,
} from "@/lib/schemas/review";

export default function ReviewPage({ params }: { params: { projectId: string } }) {
  const { projectId } = params;
  const queryClient = useQueryClient();
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [flash, setFlash] = useState<string | null>(null);

  const queueQuery = useQuery<ReviewQueueItem[]>({
    queryKey: ["review-queue", projectId],
    queryFn: () => api.get<ReviewQueueItem[]>(`/api/projects/${projectId}/review/tasks`),
  });

  const submit = useMutation<
    ReviewSubmitResponse,
    Error,
    { taskId: string; body: ReviewDecisionCreate }
  >({
    mutationFn: ({ taskId, body }) =>
      api.post<ReviewSubmitResponse>(`/api/tasks/${taskId}/review`, body),
    onSuccess: (_data, vars) => {
      setErrors((prev) => {
        if (!(vars.taskId in prev)) return prev;
        const next = { ...prev };
        delete next[vars.taskId];
        return next;
      });
      setFlash("Review submitted.");
      queryClient.invalidateQueries({ queryKey: ["review-queue", projectId] });
    },
    onError: (err, vars) => {
      setErrors((prev) => ({ ...prev, [vars.taskId]: err.message }));
    },
  });

  return (
    <AppShell projectId={projectId} section="Review">
      <h1 className="mb-6 text-2xl font-semibold">Review Queue</h1>
      <FlashMessage message={flash} onDismiss={() => setFlash(null)} />
      {queueQuery.isLoading ? (
        <p className="text-muted-foreground">Loading review queue…</p>
      ) : queueQuery.isError ? (
        <p className="text-destructive">
          Failed to load review queue:{" "}
          {queueQuery.error instanceof Error ? queueQuery.error.message : "Unknown error"}
        </p>
      ) : !queueQuery.data || queueQuery.data.length === 0 ? (
        <div className="rounded-xl border p-12 text-center text-muted-foreground">
          Review queue is empty.
        </div>
      ) : (
        <div className="space-y-4">
          {queueQuery.data.map((item) => {
            const isSubmittingThis =
              submit.isPending && submit.variables?.taskId === item.id;
            return (
              <ReviewQueueItemCard
                key={item.id}
                item={item}
                submitting={isSubmittingThis}
                errorMessage={errors[item.id]}
                onSubmit={async (body) => {
                  await submit.mutateAsync({ taskId: item.id, body });
                }}
              />
            );
          })}
        </div>
      )}
    </AppShell>
  );
}
