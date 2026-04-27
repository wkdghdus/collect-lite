"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { AppShell } from "@/components/AppShell";
import { DatasetUploader } from "@/components/DatasetUploader";
import type { DatasetResponse } from "@/lib/schemas/dataset";

export default function DatasetsPage({ params }: { params: { projectId: string } }) {
  const { projectId } = params;
  const queryClient = useQueryClient();

  const { data, isLoading, isError, error } = useQuery<DatasetResponse[]>({
    queryKey: ["datasets", projectId],
    queryFn: () => api.get<DatasetResponse[]>(`/api/projects/${projectId}/datasets`),
    retry: false,
  });

  return (
    <AppShell projectId={projectId} section="Datasets">
      <h1 className="text-2xl font-semibold mb-6">Datasets</h1>
      <div className="mb-8">
        <DatasetUploader
          projectId={projectId}
          onSuccess={() =>
            queryClient.invalidateQueries({ queryKey: ["datasets", projectId] })
          }
        />
      </div>

      <h2 className="text-lg font-semibold mb-3">Uploaded</h2>
      {isLoading ? (
        <p className="text-muted-foreground">Loading datasets…</p>
      ) : isError ? (
        <p className="text-destructive">
          Failed to load datasets: {error instanceof Error ? error.message : "Unknown error"}
        </p>
      ) : !data || data.length === 0 ? (
        <div className="rounded-xl border p-12 text-center text-muted-foreground">
          No datasets uploaded yet.
        </div>
      ) : (
        <table className="w-full text-sm border rounded-xl overflow-hidden">
          <thead className="bg-muted/50">
            <tr>
              <th className="text-left p-3">Filename</th>
              <th className="text-left p-3">Rows</th>
              <th className="text-left p-3">Status</th>
              <th className="text-left p-3">Created</th>
            </tr>
          </thead>
          <tbody>
            {data.map((d) => (
              <tr key={d.id} className="border-t">
                <td className="p-3">{d.filename}</td>
                <td className="p-3">{d.row_count}</td>
                <td className="p-3">{d.status}</td>
                <td className="p-3 text-muted-foreground">
                  {new Date(d.created_at).toISOString().slice(0, 10)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </AppShell>
  );
}
