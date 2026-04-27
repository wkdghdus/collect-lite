"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { type TaskResponse } from "@/lib/schemas/task";

interface AnnotationWorkbenchProps {
  task: TaskResponse;
  onSubmit: (label: Record<string, unknown>, confidence: number) => Promise<void>;
  onSkip: () => void;
}

export function AnnotationWorkbench({ task, onSubmit, onSkip }: AnnotationWorkbenchProps) {
  const [confidence, setConfidence] = useState(3);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit() {
    setSubmitting(true);
    try {
      await onSubmit({ task_id: task.id }, confidence);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium">Task</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-xs text-muted-foreground">ID: {task.id}</p>
          <p className="text-xs text-muted-foreground">Status: {task.status}</p>
        </CardContent>
      </Card>
      <div className="flex items-center gap-2">
        <span className="text-sm">Confidence:</span>
        {[1, 2, 3, 4, 5].map((v) => (
          <button
            key={v}
            onClick={() => setConfidence(v)}
            className={`h-8 w-8 rounded text-sm border ${confidence === v ? "bg-primary text-primary-foreground" : ""}`}
          >
            {v}
          </button>
        ))}
      </div>
      <div className="flex gap-3">
        <Button onClick={handleSubmit} disabled={submitting}>
          {submitting ? "Submitting…" : "Submit"}
        </Button>
        <Button variant="outline" onClick={onSkip}>
          Skip
        </Button>
      </div>
    </div>
  );
}
