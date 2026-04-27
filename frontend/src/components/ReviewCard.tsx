"use client";

import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export interface ReviewCardItem {
  task_id: string;
  agreement_score: number;
  annotations?: Array<{ id: string; label: unknown }>;
}

export interface ReviewDecision {
  winning_annotation_id?: string;
  resolution: "accept_a" | "accept_b" | "custom";
}

interface ReviewCardProps {
  item: ReviewCardItem;
  onResolve: (decision: ReviewDecision) => Promise<void>;
}

export function ReviewCard({ item, onResolve }: ReviewCardProps) {
  const [resolving, setResolving] = useState<ReviewDecision["resolution"] | null>(null);
  const [a, b] = item.annotations ?? [];

  async function decide(resolution: "accept_a" | "accept_b") {
    const winning = resolution === "accept_a" ? a?.id : b?.id;
    setResolving(resolution);
    try {
      await onResolve({ resolution, winning_annotation_id: winning });
    } finally {
      setResolving(null);
    }
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-mono">{item.task_id.slice(0, 8)}…</CardTitle>
          <Badge variant="secondary">{(item.agreement_score * 100).toFixed(0)}% agreement</Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-2 gap-3">
          <div>
            <p className="text-xs text-muted-foreground mb-1">Annotator A</p>
            <pre className="rounded-md bg-muted/50 p-3 text-xs overflow-x-auto">
{a ? JSON.stringify(a.label, null, 2) : "—"}
            </pre>
          </div>
          <div>
            <p className="text-xs text-muted-foreground mb-1">Annotator B</p>
            <pre className="rounded-md bg-muted/50 p-3 text-xs overflow-x-auto">
{b ? JSON.stringify(b.label, null, 2) : "—"}
            </pre>
          </div>
        </div>
        <div className="flex gap-3">
          <Button
            variant="outline"
            disabled={!a || resolving !== null}
            onClick={() => decide("accept_a")}
          >
            {resolving === "accept_a" ? "Resolving…" : "Accept A"}
          </Button>
          <Button
            variant="outline"
            disabled={!b || resolving !== null}
            onClick={() => decide("accept_b")}
          >
            {resolving === "accept_b" ? "Resolving…" : "Accept B"}
          </Button>
          <Button variant="ghost" disabled title="Custom decisions coming soon">
            Custom
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

export default ReviewCard;
