import { z } from "zod";

export const ProjectCreateSchema = z.object({
  name: z.string().min(1, "Name is required"),
  description: z.string().optional(),
  task_type: z.enum(["pairwise_preference", "relevance_rating", "classification", "extraction_qa", "freeform_critique"]),
});

export const ProjectResponseSchema = z.object({
  id: z.string().uuid(),
  name: z.string(),
  description: z.string().nullable(),
  owner_id: z.string().uuid().nullable(),
  task_type: z.string(),
  status: z.enum(["draft", "active", "paused", "completed"]),
  created_at: z.string(),
  updated_at: z.string(),
});

export type ProjectCreate = z.infer<typeof ProjectCreateSchema>;
export type ProjectResponse = z.infer<typeof ProjectResponseSchema>;
