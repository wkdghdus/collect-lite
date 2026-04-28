"use client";

import { useEffect, useRef } from "react";

type Tone = "success" | "info" | "error";

const TONES: Record<Tone, string> = {
  success: "bg-emerald-50 border-emerald-200 text-emerald-900",
  info: "bg-sky-50 border-sky-200 text-sky-900",
  error: "bg-red-50 border-red-200 text-red-900",
};

interface FlashMessageProps {
  message: string | null;
  onDismiss: () => void;
  tone?: Tone;
  durationMs?: number;
}

export function FlashMessage({
  message,
  onDismiss,
  tone = "success",
  durationMs = 3000,
}: FlashMessageProps) {
  // Hold onDismiss in a ref so the auto-dismiss timer is not reset every time
  // the parent re-renders (e.g. exports page polls every 2s while exports run).
  const dismissRef = useRef(onDismiss);
  useEffect(() => {
    dismissRef.current = onDismiss;
  }, [onDismiss]);

  useEffect(() => {
    if (!message) return;
    const id = setTimeout(() => dismissRef.current(), durationMs);
    return () => clearTimeout(id);
  }, [message, durationMs]);

  if (!message) return null;
  return (
    <div className={`mt-3 rounded border px-3 py-2 text-sm ${TONES[tone]}`}>{message}</div>
  );
}

export default FlashMessage;
