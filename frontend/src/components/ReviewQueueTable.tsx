interface ReviewTask {
  id: string;
  status: string;
  agreement_score: number;
}

interface ReviewQueueTableProps {
  tasks: ReviewTask[];
  onSelect: (taskId: string) => void;
}

export function ReviewQueueTable({ tasks, onSelect }: ReviewQueueTableProps) {
  if (tasks.length === 0) {
    return (
      <div className="rounded-xl border p-12 text-center text-muted-foreground">
        Review queue is empty.
      </div>
    );
  }
  return (
    <table className="w-full text-sm border rounded-xl overflow-hidden">
      <thead className="bg-muted/50">
        <tr>
          <th className="text-left p-3">Task ID</th>
          <th className="text-left p-3">Status</th>
          <th className="text-left p-3">Agreement</th>
          <th className="p-3"></th>
        </tr>
      </thead>
      <tbody>
        {tasks.map((task) => (
          <tr key={task.id} className="border-t">
            <td className="p-3 font-mono text-xs">{task.id.slice(0, 8)}…</td>
            <td className="p-3">{task.status}</td>
            <td className="p-3">{(task.agreement_score * 100).toFixed(0)}%</td>
            <td className="p-3">
              <button className="text-primary hover:underline text-xs" onClick={() => onSelect(task.id)}>
                Review
              </button>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
