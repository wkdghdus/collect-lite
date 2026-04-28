import { z } from "zod";

export const ProjectMetricsResponseSchema = z.object({
  total_tasks: z.number(),
  created_count: z.number(),
  suggested_count: z.number(),
  assigned_count: z.number(),
  submitted_count: z.number(),
  needs_review_count: z.number(),
  resolved_count: z.number(),
  exported_count: z.number(),
  avg_human_agreement: z.number().nullable(),
  model_human_agreement_rate: z.number().nullable(),
  final_label_distribution: z.record(z.string(), z.number()),
  exportable_task_count: z.number(),
});

export type ProjectMetricsResponse = z.infer<typeof ProjectMetricsResponseSchema>;
