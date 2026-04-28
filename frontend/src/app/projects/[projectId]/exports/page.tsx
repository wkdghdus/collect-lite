"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { AppShell } from "@/components/AppShell";
import { FlashMessage } from "@/components/FlashMessage";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { formatStatus } from "@/lib/formatStatus";
import type { ExportCreate, ExportResponse } from "@/lib/schemas/export";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const FORMATS: ExportCreate["format"][] = ["jsonl", "csv"];

const FORMAT_LABEL: Record<ExportCreate["format"], string> = {
  jsonl: "Generate JSONL export",
  csv: "Generate CSV export",
};

function isTerminal(status: ExportResponse["status"]): boolean {
  return status === "completed" || status === "failed";
}

export default function ExportsPage({ params }: { params: { projectId: string } }) {
  const { projectId } = params;
  const queryClient = useQueryClient();
  const [flash, setFlash] = useState<string | null>(null);

  const exportsQuery = useQuery<ExportResponse[]>({
    queryKey: ["exports", projectId],
    queryFn: () => api.get<ExportResponse[]>(`/api/projects/${projectId}/exports`),
    refetchInterval: (query) => {
      const data = query.state.data;
      if (!data || data.length === 0) return false;
      return data.some((exp) => !isTerminal(exp.status)) ? 2000 : false;
    },
  });

  const createExport = useMutation<ExportResponse, Error, ExportCreate>({
    mutationFn: (body) =>
      api.post<ExportResponse>(`/api/projects/${projectId}/exports`, body),
    onSuccess: () => {
      setFlash("Export queued.");
      queryClient.invalidateQueries({ queryKey: ["exports", projectId] });
    },
  });

  const exports = exportsQuery.data ?? [];

  return (
    <AppShell projectId={projectId} section="Exports">
      <h1 className="mb-6 text-2xl font-semibold">Exports</h1>

      <div className="mb-8 flex flex-wrap gap-3">
        {FORMATS.map((format) => {
          const isActive =
            createExport.isPending && createExport.variables?.format === format;
          return (
            <Button
              key={format}
              onClick={() => createExport.mutate({ format })}
              disabled={createExport.isPending}
            >
              {isActive ? "Creating…" : FORMAT_LABEL[format]}
            </Button>
          );
        })}
      </div>

      {createExport.isError ? (
        <p className="mb-6 text-sm text-destructive">
          Failed to create export: {createExport.error.message}
        </p>
      ) : null}

      <FlashMessage message={flash} onDismiss={() => setFlash(null)} />

      <h2 className="mb-3 text-lg font-semibold">Recent exports</h2>

      {exportsQuery.isLoading ? (
        <p className="text-muted-foreground">Loading exports…</p>
      ) : exportsQuery.isError ? (
        <p className="text-destructive">
          Failed to load exports:{" "}
          {exportsQuery.error instanceof Error
            ? exportsQuery.error.message
            : "Unknown error"}
        </p>
      ) : exports.length === 0 ? (
        <div className="rounded-xl border p-12 text-center text-muted-foreground">
          No exports yet. Generate one above.
        </div>
      ) : (
        <table className="w-full overflow-hidden rounded-xl border text-sm">
          <thead className="bg-muted/50">
            <tr>
              <th className="p-3 text-left">Format</th>
              <th className="p-3 text-left">Rows</th>
              <th className="p-3 text-left">Status</th>
              <th className="p-3 text-left">Created</th>
              <th className="p-3 text-left">Download</th>
            </tr>
          </thead>
          <tbody>
            {exports.map((exp) => (
              <tr key={exp.id} className="border-t">
                <td className="p-3">{exp.format.toUpperCase()}</td>
                <td className="p-3">{exp.row_count}</td>
                <td className="p-3">
                  <Badge variant={exp.status === "completed" ? "default" : "outline"}>
                    {formatStatus(exp.status)}
                  </Badge>
                </td>
                <td className="p-3 text-muted-foreground">
                  {new Date(exp.created_at).toLocaleString()}
                </td>
                <td className="p-3">
                  {exp.status === "completed" ? (
                    <a
                      href={`${API_BASE}/api/exports/${exp.id}/download`}
                      target="_blank"
                      rel="noreferrer"
                      className="text-sm text-primary hover:underline"
                    >
                      Download
                    </a>
                  ) : (
                    <span className="text-xs text-muted-foreground">
                      {formatStatus(exp.status)}
                    </span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </AppShell>
  );
}
