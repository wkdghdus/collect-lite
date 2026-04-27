"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { AppShell } from "@/components/AppShell";
import { ExportBuilder } from "@/components/ExportBuilder";
import { Badge } from "@/components/ui/badge";
import type { ExportResponse } from "@/lib/schemas/export";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

function ExportRow({ exportId }: { exportId: string }) {
  // Polls while status is not terminal. A future GET /api/projects/{id}/exports
  // list endpoint should replace this useState-based tracking.
  const { data, isError, error } = useQuery<ExportResponse>({
    queryKey: ["export", exportId],
    queryFn: () => api.get<ExportResponse>(`/api/exports/${exportId}`),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === "completed" || status === "failed" ? false : 2000;
    },
    retry: false,
  });

  if (isError) {
    return (
      <tr className="border-t">
        <td className="p-3 font-mono text-xs">{exportId.slice(0, 8)}…</td>
        <td className="p-3" colSpan={3}>
          <span className="text-destructive">
            {error instanceof Error ? error.message : "Failed to load export"}
          </span>
        </td>
      </tr>
    );
  }

  return (
    <tr className="border-t">
      <td className="p-3 font-mono text-xs">{exportId.slice(0, 8)}…</td>
      <td className="p-3">{data?.format ?? "—"}</td>
      <td className="p-3">
        <Badge variant={data?.status === "completed" ? "default" : "outline"}>
          {data?.status ?? "…"}
        </Badge>
      </td>
      <td className="p-3">
        {data?.status === "completed" ? (
          <a
            href={`${API_BASE}/api/exports/${exportId}/download`}
            target="_blank"
            rel="noreferrer"
            className="text-primary hover:underline text-sm"
          >
            Download
          </a>
        ) : (
          <span className="text-xs text-muted-foreground">Pending</span>
        )}
      </td>
    </tr>
  );
}

export default function ExportsPage({ params }: { params: { projectId: string } }) {
  const { projectId } = params;
  const [exportIds, setExportIds] = useState<string[]>([]);

  return (
    <AppShell projectId={projectId} section="Exports">
      <h1 className="text-2xl font-semibold mb-6">Exports</h1>

      <div className="mb-8">
        <ExportBuilder
          projectId={projectId}
          onCreated={(exp) => setExportIds((ids) => [exp.id, ...ids])}
        />
      </div>

      <h2 className="text-lg font-semibold mb-3">Recent</h2>
      {exportIds.length === 0 ? (
        <div className="rounded-xl border p-12 text-center text-muted-foreground">
          No exports created in this session yet.
        </div>
      ) : (
        <table className="w-full text-sm border rounded-xl overflow-hidden">
          <thead className="bg-muted/50">
            <tr>
              <th className="text-left p-3">ID</th>
              <th className="text-left p-3">Format</th>
              <th className="text-left p-3">Status</th>
              <th className="text-left p-3">Download</th>
            </tr>
          </thead>
          <tbody>
            {exportIds.map((id) => (
              <ExportRow key={id} exportId={id} />
            ))}
          </tbody>
        </table>
      )}
    </AppShell>
  );
}
