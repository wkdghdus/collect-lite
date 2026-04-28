"use client";

import { Badge } from "@/components/ui/badge";
import { formatStatus } from "@/lib/formatStatus";
import type { TaskResponse } from "@/lib/schemas/task";

interface TaskQueueTableProps {
  tasks: TaskResponse[];
  onSelect: (taskId: string) => void;
}

const statusVariant: Record<string, "default" | "secondary" | "outline" | "destructive"> = {
  created: "outline",
  suggested: "secondary",
  assigned: "default",
  submitted: "default",
  needs_review: "destructive",
  resolved: "secondary",
  exported: "secondary",
};

function truncateId(id: string): string {
  return `${id.slice(0, 8)}…`;
}

function formatDate(iso: string): string {
  return new Date(iso).toISOString().slice(0, 10);
}

export function TaskQueueTable({ tasks, onSelect }: TaskQueueTableProps) {
  if (tasks.length === 0) {
    return (
      <div className="rounded-xl border p-12 text-center text-muted-foreground">
        No tasks yet — click Generate Tasks to begin.
      </div>
    );
  }

  return (
    <table className="w-full text-sm border rounded-xl overflow-hidden">
      <thead className="bg-muted/50">
        <tr>
          <th className="text-left p-3">Task ID</th>
          <th className="text-left p-3">Status</th>
          <th className="text-left p-3">Priority</th>
          <th className="text-left p-3">Required</th>
          <th className="text-left p-3">Created</th>
        </tr>
      </thead>
      <tbody>
        {tasks.map((task) => (
          <tr
            key={task.id}
            onClick={() => onSelect(task.id)}
            className="border-t cursor-pointer hover:bg-muted/30"
          >
            <td className="p-3 font-mono text-xs">{truncateId(task.id)}</td>
            <td className="p-3">
              <Badge variant={statusVariant[task.status] ?? "outline"}>{formatStatus(task.status)}</Badge>
            </td>
            <td className="p-3">{task.priority}</td>
            <td className="p-3">{task.required_annotations}</td>
            <td className="p-3 text-muted-foreground">{formatDate(task.created_at)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export default TaskQueueTable;
