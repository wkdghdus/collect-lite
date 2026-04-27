"use client";

import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { TaskResponse } from "@/lib/schemas/task";

interface AnnotationCardProps {
  task: TaskResponse;
  onSubmit: (label: Record<string, unknown>, confidence: number) => Promise<void>;
  onSkip: () => Promise<void>;
}

export function AnnotationCard({ task, onSubmit, onSkip }: AnnotationCardProps) {
  const [confidence, setConfidence] = useState(3);
  const [submitting, setSubmitting] = useState(false);
  const [skipping, setSkipping] = useState(false);

  async function handleSubmit() {
    setSubmitting(true);
    try {
      await onSubmit({}, confidence);
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

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-medium font-mono">{task.id.slice(0, 8)}…</CardTitle>
          <Badge variant="outline">{task.status}</Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* TODO: render per-task-type rich UI (pairwise / rating / classification / extraction). */}
        <pre className="rounded-md bg-muted/50 p-4 text-xs overflow-x-auto">
{JSON.stringify(task, null, 2)}
        </pre>
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
          <Button onClick={handleSubmit} disabled={busy}>
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
