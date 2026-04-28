import { z } from "zod";

export const TaskResponseSchema = z.object({
  id: z.string().uuid(),
  project_id: z.string().uuid(),
  example_id: z.string().uuid(),
  template_id: z.string().uuid(),
  status: z.enum(["created", "suggested", "assigned", "submitted", "needs_review", "resolved", "exported"]),
  priority: z.number(),
  required_annotations: z.number(),
  annotation_count: z.number().default(0),
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

export const ModelSuggestionPayloadSchema = z.object({
  provider: z.string(),
  model_name: z.string(),
  score: z.number().nullable().optional(),
  suggested_label: z.string().nullable().optional(),
  created_at: z.string(),
});

export type ModelSuggestionPayload = z.infer<typeof ModelSuggestionPayloadSchema>;

export const AnnotationSummarySchema = z.object({
  id: z.string().uuid(),
  label: z.record(z.unknown()),
  confidence: z.number().int().nullable().optional(),
  notes: z.string().nullable().optional(),
  created_at: z.string(),
});

export type AnnotationSummary = z.infer<typeof AnnotationSummarySchema>;

export const TaskDetailResponseSchema = TaskResponseSchema.extend({
  source_example_id: z.string().uuid(),
  dataset_id: z.string().uuid().nullable().optional(),
  query: z.string().default(""),
  candidate_document: z.string().default(""),
  document_id: z.string().nullable().optional(),
  example_metadata: z.record(z.unknown()).default({}),
  model_suggestion: ModelSuggestionPayloadSchema.nullable().optional(),
  annotations: z.array(AnnotationSummarySchema).default([]),
});

export type TaskDetailResponse = z.infer<typeof TaskDetailResponseSchema>;
