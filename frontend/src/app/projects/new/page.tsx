"use client";

import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { AppShell } from "@/components/AppShell";
import { Button } from "@/components/ui/button";
import {
  ProjectCreateSchema,
  type ProjectCreate,
  type ProjectResponse,
} from "@/lib/schemas/project";

const TASK_TYPES: { value: ProjectCreate["task_type"]; comingSoon: boolean }[] = [
  { value: "rag_relevance", comingSoon: false },
  { value: "pairwise_preference", comingSoon: true },
  { value: "relevance_rating", comingSoon: true },
  { value: "classification", comingSoon: true },
  { value: "extraction_qa", comingSoon: true },
  { value: "freeform_critique", comingSoon: true },
];

const inputClass =
  "w-full rounded-md border border-input bg-background px-3 py-2 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring";

export default function NewProjectPage() {
  const router = useRouter();
  const queryClient = useQueryClient();

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<ProjectCreate>({
    resolver: zodResolver(ProjectCreateSchema),
    defaultValues: { name: "", description: "", task_type: "rag_relevance" },
  });

  const mutation = useMutation({
    mutationFn: (body: ProjectCreate) =>
      api.post<ProjectResponse>("/api/projects", body),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["projects"] });
      router.push(`/projects/${data.id}`);
    },
  });

  return (
    <AppShell>
      <h1 className="text-2xl font-semibold mb-6">Create Project</h1>
      <form
        className="max-w-xl space-y-4"
        onSubmit={handleSubmit((data) => mutation.mutate(data))}
      >
        <div>
          <label className="text-sm font-medium block mb-1" htmlFor="name">
            Name
          </label>
          <input id="name" className={inputClass} {...register("name")} />
          {errors.name ? (
            <p className="text-sm text-destructive mt-1">{errors.name.message}</p>
          ) : null}
        </div>

        <div>
          <label className="text-sm font-medium block mb-1" htmlFor="description">
            Description
          </label>
          <textarea
            id="description"
            rows={3}
            className={inputClass}
            {...register("description")}
          />
          {errors.description ? (
            <p className="text-sm text-destructive mt-1">{errors.description.message}</p>
          ) : null}
        </div>

        <div>
          <label className="text-sm font-medium block mb-1" htmlFor="task_type">
            Task Type
          </label>
          <select id="task_type" className={inputClass} {...register("task_type")}>
            {TASK_TYPES.map((t) => (
              <option key={t.value} value={t.value} disabled={t.comingSoon}>
                {t.comingSoon ? `${t.value} (coming soon)` : t.value}
              </option>
            ))}
          </select>
          {errors.task_type ? (
            <p className="text-sm text-destructive mt-1">{errors.task_type.message}</p>
          ) : null}
        </div>

        {mutation.isError ? (
          <p className="text-sm text-destructive">
            {mutation.error instanceof Error ? mutation.error.message : "Failed to create project"}
          </p>
        ) : null}

        <div className="flex gap-3">
          <Button type="submit" disabled={mutation.isPending}>
            {mutation.isPending ? "Creating…" : "Create Project"}
          </Button>
          <Button type="button" variant="outline" onClick={() => router.back()}>
            Cancel
          </Button>
        </div>
      </form>
    </AppShell>
  );
}
