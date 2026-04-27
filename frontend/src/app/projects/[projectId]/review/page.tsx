"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { AppShell } from "@/components/AppShell";
import { ReviewCard, type ReviewCardItem, type ReviewDecision } from "@/components/ReviewCard";

export default function ReviewPage({ params }: { params: { projectId: string } }) {
  const { projectId } = params;
  const queryClient = useQueryClient();

  const { data, isLoading, isError, error } = useQuery<ReviewCardItem[]>({
    queryKey: ["review-queue", projectId],
    queryFn: () => api.get<ReviewCardItem[]>(`/api/projects/${projectId}/review-queue`),
    retry: false,
  });

  const resolve = useMutation({
    mutationFn: ({ taskId, decision }: { taskId: string; decision: ReviewDecision }) =>
      api.post(`/api/reviews/${taskId}/resolve`, decision),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["review-queue", projectId] }),
  });

  return (
    <AppShell projectId={projectId} section="Review">
      <h1 className="text-2xl font-semibold mb-6">Review Queue</h1>
      {isLoading ? (
        <p className="text-muted-foreground">Loading review queue…</p>
      ) : isError ? (
        <div className="rounded-xl border p-12 text-center text-muted-foreground">
          Review queue is empty.
          <p className="text-xs mt-2">
            ({error instanceof Error ? error.message : "endpoint not yet available"})
          </p>
        </div>
      ) : !data || data.length === 0 ? (
        <div className="rounded-xl border p-12 text-center text-muted-foreground">
          Review queue is empty.
        </div>
      ) : (
        <div className="space-y-4">
          {data.map((item) => (
            <ReviewCard
              key={item.task_id}
              item={item}
              onResolve={async (decision) => {
                await resolve.mutateAsync({ taskId: item.task_id, decision });
              }}
            />
          ))}
        </div>
      )}
    </AppShell>
  );
}
