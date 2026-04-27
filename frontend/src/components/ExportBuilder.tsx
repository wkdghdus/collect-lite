"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import type { ExportResponse } from "@/lib/schemas/export";

interface ExportBuilderProps {
  projectId: string;
  onCreated?: (exp: ExportResponse) => void;
}

export function ExportBuilder({ projectId, onCreated }: ExportBuilderProps) {
  const [format, setFormat] = useState<"jsonl" | "csv">("jsonl");
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleCreate() {
    setCreating(true);
    setError(null);
    try {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/projects/${projectId}/exports`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ format }),
        },
      );
      if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
      const body = (await res.json()) as ExportResponse;
      onCreated?.(body);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      setCreating(false);
    }
  }

  return (
    <div className="rounded-xl border p-6 space-y-4">
      <h2 className="font-semibold">Create Export</h2>
      <div className="flex gap-3">
        {(["jsonl", "csv"] as const).map((f) => (
          <button
            key={f}
            onClick={() => setFormat(f)}
            className={`rounded-md border px-4 py-2 text-sm ${
              format === f ? "bg-primary text-primary-foreground" : ""
            }`}
          >
            {f.toUpperCase()}
          </button>
        ))}
      </div>
      <Button onClick={handleCreate} disabled={creating}>
        {creating ? "Creating…" : "Create Export"}
      </Button>
      {error ? <p className="text-sm text-destructive">{error}</p> : null}
    </div>
  );
}

export default ExportBuilder;
