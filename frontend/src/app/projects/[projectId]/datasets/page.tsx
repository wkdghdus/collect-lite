export default function DatasetsPage({ params }: { params: { projectId: string } }) {
  return (
    <main className="container mx-auto p-8">
      <h1 className="text-2xl font-semibold mb-8">Datasets</h1>
      <div className="rounded-xl border border-dashed p-12 text-center text-muted-foreground">
        <p className="mb-4">Upload a CSV or JSONL file to create annotation tasks.</p>
        <button className="rounded-md bg-primary px-4 py-2 text-sm text-primary-foreground">
          Upload Dataset
        </button>
      </div>
    </main>
  );
}
