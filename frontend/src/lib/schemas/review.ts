import { z } from "zod";

import { TaskResponseSchema } from "./task";

export const ReviewLabelSchema = z.enum(["relevant", "partially_relevant", "not_relevant"]);
export type ReviewLabel = z.infer<typeof ReviewLabelSchema>;

export const AnnotationSummarySchema = z.object({
  id: z.string().uuid(),
  label: z.record(z.unknown()),
  confidence: z.number().int().nullable().optional(),
  notes: z.string().nullable().optional(),
  created_at: z.string(),
});
export type AnnotationSummary = z.infer<typeof AnnotationSummarySchema>;

export const ModelSuggestionPayloadSchema = z.object({
  provider: z.string(),
  model_name: z.string(),
  score: z.number().nullable().optional(),
  suggested_label: z.string().nullable().optional(),
  created_at: z.string(),
});
export type ModelSuggestionPayload = z.infer<typeof ModelSuggestionPayloadSchema>;

export const ConsensusResultSchema = z.object({
  id: z.string().uuid(),
  task_id: z.string().uuid(),
  final_label: z.record(z.unknown()),
  agreement_score: z.number(),
  method: z.string(),
  num_annotations: z.number().int(),
  status: z.enum(["auto_resolved", "needs_review", "review_resolved"]),
  created_at: z.string(),
});
export type ConsensusResult = z.infer<typeof ConsensusResultSchema>;

export const ReviewQueueItemSchema = TaskResponseSchema.extend({
  source_example_id: z.string().uuid(),
  dataset_id: z.string().uuid().nullable().optional(),
  query: z.string().default(""),
  candidate_document: z.string().default(""),
  document_id: z.string().nullable().optional(),
  example_metadata: z.record(z.unknown()).default({}),
  model_suggestion: ModelSuggestionPayloadSchema.nullable().optional(),
  annotations: z.array(AnnotationSummarySchema).default([]),
  consensus: ConsensusResultSchema.nullable().optional(),
});
export type ReviewQueueItem = z.infer<typeof ReviewQueueItemSchema>;

export const ReviewDecisionCreateSchema = z.object({
  final_label: ReviewLabelSchema,
  reason: z.string().optional(),
  reviewer_id: z.string().uuid().optional(),
});
export type ReviewDecisionCreate = z.infer<typeof ReviewDecisionCreateSchema>;

export const ReviewDecisionResponseSchema = z.object({
  id: z.string().uuid(),
  task_id: z.string().uuid(),
  reviewer_id: z.string().uuid(),
  final_label: z.record(z.unknown()),
  reason: z.string().nullable().optional(),
  created_at: z.string(),
});
export type ReviewDecisionResponse = z.infer<typeof ReviewDecisionResponseSchema>;

export const ReviewSubmitResponseSchema = z.object({
  review: ReviewDecisionResponseSchema,
  task_status: z.string(),
});
export type ReviewSubmitResponse = z.infer<typeof ReviewSubmitResponseSchema>;
