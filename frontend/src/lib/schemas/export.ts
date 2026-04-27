import { z } from "zod";

export const ExportCreateSchema = z.object({
  format: z.enum(["jsonl", "csv"]).default("jsonl"),
});

export const ExportResponseSchema = z.object({
  id: z.string().uuid(),
  project_id: z.string().uuid(),
  format: z.enum(["jsonl", "csv"]),
  status: z.enum(["queued", "running", "completed", "failed"]),
  file_path: z.string().nullable(),
  schema_version: z.string(),
  created_at: z.string(),
});

export type ExportCreate = z.infer<typeof ExportCreateSchema>;
export type ExportResponse = z.infer<typeof ExportResponseSchema>;
