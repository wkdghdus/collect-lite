"use client";

import { useState } from "react";

import { ConsensusBadge } from "@/components/ConsensusBadge";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { ReviewLabel, ReviewQueueItem } from "@/lib/schemas/review";

const LABELS: ReviewLabel[] = ["relevant", "partially_relevant", "not_relevant"];

interface ReviewQueueItemCardProps {
  item: ReviewQueueItem;
  onSubmit: (body: { final_label: ReviewLabel; reason?: string }) => Promise<void>;
  submitting?: boolean;
  errorMessage?: string;
}

export function ReviewQueueItemCard({
  item,
  onSubmit,
  submitting = false,
  errorMessage,
}: ReviewQueueItemCardProps) {
  const [label, setLabel] = useState<ReviewLabel | null>(null);
  const [reason, setReason] = useState("");

  async function handleSubmit() {
    if (!label) return;
    await onSubmit({ final_label: label, reason: reason.trim() || undefined });
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="font-mono text-sm">{item.id.slice(0, 8)}…</CardTitle>
          {item.consensus ? (
            <ConsensusBadge
              agreementScore={item.consensus.agreement_score}
              status={item.consensus.status}
            />
          ) : (
            <Badge variant="outline">consensus pending</Badge>
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <section className="space-y-1">
          <p className="text-xs font-medium text-muted-foreground">Query</p>
          <p className="text-sm">{item.query || "—"}</p>
        </section>

        <section className="space-y-1">
          <p className="text-xs font-medium text-muted-foreground">Candidate document</p>
          <pre className="rounded-md bg-muted/50 p-3 text-xs whitespace-pre-wrap">
            {item.candidate_document || "—"}
          </pre>
        </section>

        <section className="space-y-1">
          <p className="text-xs font-medium text-muted-foreground">
            Annotations ({item.annotations.length})
          </p>
          {item.annotations.length === 0 ? (
            <p className="text-sm text-muted-foreground">No annotations yet.</p>
          ) : (
            <ul className="space-y-1 text-xs">
              {item.annotations.map((a) => (
                <li key={a.id} className="rounded border bg-muted/30 p-2 font-mono">
                  <span>{JSON.stringify(a.label)}</span>
                  {a.confidence != null ? (
                    <span className="ml-2 text-muted-foreground">conf {a.confidence}</span>
                  ) : null}
                  {a.notes ? (
                    <span className="ml-2 text-muted-foreground">— {a.notes}</span>
                  ) : null}
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className="space-y-1">
          <p className="text-xs font-medium text-muted-foreground">Model suggestion</p>
          {item.model_suggestion ? (
            <p className="text-sm">
              {item.model_suggestion.provider} / {item.model_suggestion.model_name} →{" "}
              <strong>{item.model_suggestion.suggested_label ?? "—"}</strong>
              {item.model_suggestion.score != null
                ? ` (${(item.model_suggestion.score * 100).toFixed(0)}%)`
                : null}
            </p>
          ) : (
            <p className="text-sm text-muted-foreground">No model suggestion.</p>
          )}
        </section>

        {item.consensus ? (
          <section className="space-y-1">
            <p className="text-xs font-medium text-muted-foreground">Consensus</p>
            <p className="text-xs">
              {item.consensus.method} · {item.consensus.num_annotations} annotations · status{" "}
              <code>{item.consensus.status}</code>
            </p>
            <pre className="rounded-md bg-muted/30 p-2 text-xs">
              {JSON.stringify(item.consensus.final_label, null, 2)}
            </pre>
          </section>
        ) : null}

        <section className="space-y-2 border-t pt-4">
          <p className="text-xs font-medium text-muted-foreground">Final label</p>
          <div className="flex gap-2">
            {LABELS.map((option) => (
              <Button
                key={option}
                type="button"
                variant={label === option ? "default" : "outline"}
                size="sm"
                onClick={() => setLabel(option)}
                disabled={submitting}
              >
                {option}
              </Button>
            ))}
          </div>
          <textarea
            className="w-full rounded-md border bg-background p-2 text-sm"
            rows={2}
            placeholder="Reason (optional)"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            disabled={submitting}
          />
          {errorMessage ? <p className="text-xs text-destructive">{errorMessage}</p> : null}
          <div className="flex justify-end">
            <Button onClick={handleSubmit} disabled={!label || submitting}>
              {submitting ? "Submitting…" : "Submit decision"}
            </Button>
          </div>
        </section>
      </CardContent>
    </Card>
  );
}

export default ReviewQueueItemCard;
