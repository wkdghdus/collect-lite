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

export const ModelSuggestionResponseSchema = z.object({
  id: z.string().uuid(),
  task_id: z.string().uuid(),
  provider: z.string(),
  model_name: z.string(),
  suggestion: z.record(z.unknown()),
  confidence: z.number().nullable(),
  raw_response: z.record(z.unknown()).nullable(),
  created_at: z.string(),
});

export type ModelSuggestionResponse = z.infer<typeof ModelSuggestionResponseSchema>;

export const TaskTemplateResponseSchema = z.object({
  id: z.string().uuid(),
  project_id: z.string().uuid(),
  name: z.string(),
  instructions: z.string(),
  label_schema: z.record(z.unknown()),
  version: z.number(),
  created_at: z.string(),
});

export type TaskTemplateResponse = z.infer<typeof TaskTemplateResponseSchema>;
