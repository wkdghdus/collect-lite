import { Badge } from "@/components/ui/badge";

interface ConsensusBadgeProps {
  agreementScore: number;
  status: "auto_resolved" | "needs_review" | "review_resolved";
}

export function ConsensusBadge({ agreementScore, status }: ConsensusBadgeProps) {
  const variant = status === "auto_resolved" && agreementScore >= 0.8
    ? "default"
    : status === "review_resolved"
    ? "secondary"
    : "destructive";

  return (
    <Badge variant={variant}>
      {(agreementScore * 100).toFixed(0)}% agreement
    </Badge>
  );
}
