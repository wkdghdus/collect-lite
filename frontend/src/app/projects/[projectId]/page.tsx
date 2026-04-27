export default function ProjectDetailPage({ params }: { params: { projectId: string } }) {
  return (
    <main className="container mx-auto p-8">
      <h1 className="text-2xl font-semibold mb-2">Project</h1>
      <p className="text-sm text-muted-foreground mb-8">ID: {params.projectId}</p>
      <nav className="flex gap-4 mb-8 text-sm">
        <a href="datasets" className="hover:underline">Datasets</a>
        <a href="tasks" className="hover:underline">Tasks</a>
        <a href="review" className="hover:underline">Review Queue</a>
        <a href="metrics" className="hover:underline">Metrics</a>
      </nav>
      <div className="rounded-xl border p-8 text-muted-foreground text-center">
        Project overview coming soon.
      </div>
    </main>
  );
}
