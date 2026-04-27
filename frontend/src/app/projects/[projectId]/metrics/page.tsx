export default function MetricsPage({ params }: { params: { projectId: string } }) {
  return (
    <main className="container mx-auto p-8">
      <h1 className="text-2xl font-semibold mb-8">Metrics</h1>
      <div className="grid grid-cols-2 gap-4 mb-8">
        {[
          { label: "Agreement Rate", value: "—" },
          { label: "Gold Accuracy", value: "—" },
          { label: "Model-Human Disagreement", value: "—" },
          { label: "Review Backlog", value: "0" },
        ].map(({ label, value }) => (
          <div key={label} className="rounded-xl border p-6">
            <p className="text-sm text-muted-foreground">{label}</p>
            <p className="text-3xl font-bold mt-1">{value}</p>
          </div>
        ))}
      </div>
      <div className="rounded-xl border p-12 text-center text-muted-foreground">
        Charts will render here once annotation data is available.
      </div>
    </main>
  );
}
