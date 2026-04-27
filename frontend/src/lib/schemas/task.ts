import { z } from "zod";

export const TaskResponseSchema = z.object({
  id: z.string().uuid(),
  project_id: z.string().uuid(),
  example_id: z.string().uuid(),
  template_id: z.string().uuid(),
  status: z.enum(["created", "suggested", "assigned", "submitted", "needs_review", "resolved", "exported"]),
  priority: z.number(),
  required_annotations: z.number(),
  created_at: z.string(),
  updated_at: z.string(),
});

export type TaskResponse = z.infer<typeof TaskResponseSchema>;
