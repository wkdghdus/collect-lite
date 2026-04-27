"use client";

import { useRef, useState } from "react";
import { Button } from "@/components/ui/button";

interface DatasetUploaderProps {
  projectId: string;
  onSuccess?: () => void;
}

export function DatasetUploader({ projectId, onSuccess }: DatasetUploaderProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleFile(file: File) {
    setUploading(true);
    setError(null);
    try {
      const formData = new FormData();
      formData.append("file", file);
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/projects/${projectId}/datasets`,
        { method: "POST", body: formData }
      );
      if (!res.ok) throw new Error(`Upload failed: ${res.statusText}`);
      onSuccess?.();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      setUploading(false);
    }
  }

  return (
    <div className="rounded-xl border border-dashed p-12 text-center">
      <p className="text-sm text-muted-foreground mb-4">Upload a CSV or JSONL file</p>
      <Button variant="outline" onClick={() => inputRef.current?.click()} disabled={uploading}>
        {uploading ? "Uploading…" : "Choose File"}
      </Button>
      <input
        ref={inputRef}
        type="file"
        accept=".csv,.jsonl"
        className="hidden"
        onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])}
      />
      {error && <p className="text-sm text-destructive mt-3">{error}</p>}
    </div>
  );
}
