interface ModelSuggestionPanelProps {
  suggestion: {
    provider: string;
    model_name: string;
    suggestion: Record<string, unknown>;
    confidence: number | null;
  } | null;
}

export function ModelSuggestionPanel({ suggestion }: ModelSuggestionPanelProps) {
  if (!suggestion) return null;
  return (
    <div className="rounded-xl border bg-muted/30 p-4">
      <p className="text-xs font-medium text-muted-foreground mb-2">
        Model Suggestion — {suggestion.provider} / {suggestion.model_name}
        {suggestion.confidence != null && ` (confidence: ${(suggestion.confidence * 100).toFixed(0)}%)`}
      </p>
      <pre className="text-xs whitespace-pre-wrap">{JSON.stringify(suggestion.suggestion, null, 2)}</pre>
    </div>
  );
}
