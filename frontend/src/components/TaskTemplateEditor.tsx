"use client";

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Button } from "@/components/ui/button";

const schema = z.object({
  name: z.string().min(1, "Name is required"),
  instructions: z.string().min(10, "Instructions must be at least 10 characters"),
});

type FormValues = z.infer<typeof schema>;

interface TaskTemplateEditorProps {
  onSave: (values: FormValues) => Promise<void>;
}

export function TaskTemplateEditor({ onSave }: TaskTemplateEditorProps) {
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<FormValues>({
    resolver: zodResolver(schema),
  });

  return (
    <form onSubmit={handleSubmit(onSave)} className="space-y-4">
      <div>
        <label className="block text-sm font-medium mb-1">Template Name</label>
        <input
          {...register("name")}
          className="w-full rounded-md border px-3 py-2 text-sm"
          placeholder="e.g. Relevance Rating v1"
        />
        {errors.name && <p className="text-xs text-destructive mt-1">{errors.name.message}</p>}
      </div>
      <div>
        <label className="block text-sm font-medium mb-1">Instructions</label>
        <textarea
          {...register("instructions")}
          rows={6}
          className="w-full rounded-md border px-3 py-2 text-sm"
          placeholder="Write clear labeling instructions for annotators…"
        />
        {errors.instructions && (
          <p className="text-xs text-destructive mt-1">{errors.instructions.message}</p>
        )}
      </div>
      <Button type="submit" disabled={isSubmitting}>
        {isSubmitting ? "Saving…" : "Save Template"}
      </Button>
    </form>
  );
}
