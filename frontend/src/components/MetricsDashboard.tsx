import { MetricsCard } from "@/components/MetricsCard";

interface Metrics {
  tasks_total: number;
  tasks_resolved: number;
  review_backlog: number;
  agreement_rate: number;
  gold_accuracy: number;
  model_human_disagreement_rate: number;
  avg_annotation_latency_ms: number;
}

interface MetricsDashboardProps {
  metrics: Metrics | null;
}

export function MetricsDashboard({ metrics }: MetricsDashboardProps) {
  if (!metrics) {
    return <div className="text-center text-muted-foreground p-12">Loading metrics…</div>;
  }
  const cards = [
    { label: "Tasks Total", value: metrics.tasks_total },
    { label: "Tasks Resolved", value: metrics.tasks_resolved },
    { label: "Review Backlog", value: metrics.review_backlog },
    { label: "Agreement Rate", value: `${(metrics.agreement_rate * 100).toFixed(1)}%` },
    { label: "Gold Accuracy", value: `${(metrics.gold_accuracy * 100).toFixed(1)}%` },
    {
      label: "Model-Human Disagreement",
      value: `${(metrics.model_human_disagreement_rate * 100).toFixed(1)}%`,
    },
  ];
  return (
    <div className="grid grid-cols-3 gap-4">
      {cards.map(({ label, value }) => (
        <MetricsCard key={label} label={label} value={value} />
      ))}
    </div>
  );
}

export default MetricsDashboard;
