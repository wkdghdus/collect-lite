export default function ExportsPage() {
  return (
    <main className="container mx-auto p-8">
      <h1 className="text-2xl font-semibold mb-8">Exports</h1>
      <div className="rounded-xl border p-12 text-center text-muted-foreground">
        <p className="mb-4">Export resolved tasks as JSONL or CSV for training and evaluation.</p>
        <button className="rounded-md bg-primary px-4 py-2 text-sm text-primary-foreground">
          Create Export
        </button>
      </div>
    </main>
  );
}
