import { z } from "zod";

export const UserResponseSchema = z.object({
  id: z.string().uuid(),
  email: z.string(),
  name: z.string(),
  role: z.string(),
  created_at: z.string(),
});

export type UserResponse = z.infer<typeof UserResponseSchema>;
