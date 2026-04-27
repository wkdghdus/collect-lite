export default function TasksPage({ params }: { params: { projectId: string } }) {
  return (
    <main className="container mx-auto p-8">
      <h1 className="text-2xl font-semibold mb-8">Tasks</h1>
      <div className="grid grid-cols-3 gap-4 mb-8">
        {["Created", "In Progress", "Resolved"].map((label) => (
          <div key={label} className="rounded-xl border p-6">
            <p className="text-sm text-muted-foreground">{label}</p>
            <p className="text-3xl font-bold mt-1">0</p>
          </div>
        ))}
      </div>
      <div className="flex gap-3">
        <button className="rounded-md bg-primary px-4 py-2 text-sm text-primary-foreground">
          Generate Tasks
        </button>
        <button className="rounded-md border px-4 py-2 text-sm">
          Run Model Suggestions
        </button>
      </div>
    </main>
  );
}
