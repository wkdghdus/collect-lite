import { z } from "zod";

export const AnnotationCreateSchema = z.object({
  label: z.record(z.unknown()),
  confidence: z.number().min(1).max(5).optional(),
  notes: z.string().optional(),
  model_suggestion_visible: z.boolean().default(true),
  latency_ms: z.number().optional(),
});

export type AnnotationCreate = z.infer<typeof AnnotationCreateSchema>;
