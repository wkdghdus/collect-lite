"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { ProjectResponse } from "@/lib/schemas/project";

interface AppShellProps {
  children: React.ReactNode;
  projectId?: string;
  section?: string;
}

export function AppShell({ children, projectId, section }: AppShellProps) {
  const { data: project } = useQuery<ProjectResponse>({
    queryKey: ["projects", projectId],
    queryFn: () => api.get<ProjectResponse>(`/api/projects/${projectId}`),
    enabled: Boolean(projectId),
  });

  return (
    <div className="min-h-screen bg-background text-foreground">
      <header className="border-b">
        <div className="container mx-auto flex items-center justify-between px-8 py-4">
          <Link href="/" className="text-lg font-semibold tracking-tight">
            CollectLite
          </Link>
          {projectId ? (
            <nav className="text-sm text-muted-foreground">
              <Link href="/" className="hover:underline">
                Projects
              </Link>
              <span className="mx-2">/</span>
              <Link href={`/projects/${projectId}`} className="hover:underline">
                {project?.name ?? "…"}
              </Link>
              {section ? (
                <>
                  <span className="mx-2">/</span>
                  <span className="text-foreground">{section}</span>
                </>
              ) : null}
            </nav>
          ) : null}
        </div>
      </header>
      <main className="container mx-auto p-8">{children}</main>
    </div>
  );
}

export default AppShell;
