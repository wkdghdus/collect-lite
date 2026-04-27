import { Card, CardContent } from "@/components/ui/card";

interface MetricsCardProps {
  label: string;
  value: string | number;
  hint?: string;
}

export function MetricsCard({ label, value, hint }: MetricsCardProps) {
  return (
    <Card>
      <CardContent className="p-6">
        <p className="text-sm text-muted-foreground">{label}</p>
        <p className="text-3xl font-bold mt-1">{value}</p>
        {hint ? <p className="text-xs text-muted-foreground mt-2">{hint}</p> : null}
      </CardContent>
    </Card>
  );
}

export default MetricsCard;
