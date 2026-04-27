import { z } from "zod";

export const DatasetResponseSchema = z.object({
  id: z.string().uuid(),
  project_id: z.string().uuid(),
  filename: z.string(),
  schema_version: z.string(),
  row_count: z.number(),
  status: z.enum(["uploaded", "validated", "failed"]),
  created_at: z.string(),
});

export type DatasetResponse = z.infer<typeof DatasetResponseSchema>;
