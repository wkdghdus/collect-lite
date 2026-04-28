"use client";

import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { formatStatus } from "@/lib/formatStatus";
import type { TaskDetailResponse, TaskResponse } from "@/lib/schemas/task";

const RELEVANCE_OPTIONS = ["relevant", "partially_relevant", "not_relevant"] as const;
type RelevanceValue = (typeof RELEVANCE_OPTIONS)[number];

interface AnnotationCardProps {
  task: TaskResponse | TaskDetailResponse;
  taskType: string;
  onSubmit: (label: Record<string, unknown>, confidence: number) => Promise<void>;
  onSkip: () => Promise<void>;
  submitDisabled?: boolean;
}

function isDetail(task: TaskResponse | TaskDetailResponse): task is TaskDetailResponse {
  return "query" in task && "candidate_document" in task;
}

export function AnnotationCard({
  task,
  taskType,
  onSubmit,
  onSkip,
  submitDisabled,
}: AnnotationCardProps) {
  const [confidence, setConfidence] = useState(3);
  const [submitting, setSubmitting] = useState(false);
  const [skipping, setSkipping] = useState(false);
  const [relevance, setRelevance] = useState<RelevanceValue | null>(null);

  const isRagRelevance = taskType === "rag_relevance";
  const detail = isDetail(task) ? task : null;

  async function handleSubmit() {
    if (isRagRelevance && !relevance) return;
    setSubmitting(true);
    try {
      const label: Record<string, unknown> = isRagRelevance ? { relevance } : {};
      await onSubmit(label, confidence);
    } finally {
      setSubmitting(false);
    }
  }

  async function handleSkip() {
    setSkipping(true);
    try {
      await onSkip();
    } finally {
      setSkipping(false);
    }
  }

  const busy = submitting || skipping;
  const submitLocked =
    busy || submitDisabled === true || (isRagRelevance && !relevance);

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-medium font-mono">{task.id.slice(0, 8)}…</CardTitle>
          <Badge variant="outline">{formatStatus(task.status)}</Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {detail ? (
          <div className="space-y-3">
            <div>
              <p className="text-xs uppercase tracking-wide text-muted-foreground mb-1">
                Query
              </p>
              <p className="rounded-md bg-muted/50 p-3 text-sm whitespace-pre-wrap">
                {detail.query || "(empty)"}
              </p>
            </div>
            <div>
              <p className="text-xs uppercase tracking-wide text-muted-foreground mb-1">
                Candidate document
              </p>
              <p className="rounded-md bg-muted/50 p-3 text-sm whitespace-pre-wrap">
                {detail.candidate_document || "(empty)"}
              </p>
            </div>
          </div>
        ) : (
          <pre className="rounded-md bg-muted/50 p-4 text-xs overflow-x-auto">
{JSON.stringify(task, null, 2)}
          </pre>
        )}

        {isRagRelevance ? (
          <fieldset className="space-y-2">
            <legend className="text-sm font-medium">Relevance label</legend>
            <div className="flex flex-wrap gap-3">
              {RELEVANCE_OPTIONS.map((option) => (
                <label
                  key={option}
                  className={`flex items-center gap-2 rounded-md border px-3 py-2 text-sm cursor-pointer ${
                    relevance === option ? "border-primary bg-primary/10" : ""
                  }`}
                >
                  <input
                    type="radio"
                    name="relevance"
                    value={option}
                    checked={relevance === option}
                    onChange={() => setRelevance(option)}
                    disabled={busy}
                  />
                  {formatStatus(option)}
                </label>
              ))}
            </div>
          </fieldset>
        ) : null}

        <div className="flex items-center gap-2">
          <span className="text-sm">Confidence:</span>
          {[1, 2, 3, 4, 5].map((v) => (
            <button
              key={v}
              type="button"
              onClick={() => setConfidence(v)}
              disabled={busy}
              className={`h-8 w-8 rounded text-sm border ${
                confidence === v ? "bg-primary text-primary-foreground" : ""
              }`}
            >
              {v}
            </button>
          ))}
        </div>
        <div className="flex gap-3">
          <Button onClick={handleSubmit} disabled={submitLocked}>
            {submitting ? "Submitting…" : "Submit"}
          </Button>
          <Button variant="outline" onClick={handleSkip} disabled={busy}>
            {skipping ? "Skipping…" : "Skip"}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

export default AnnotationCard;
