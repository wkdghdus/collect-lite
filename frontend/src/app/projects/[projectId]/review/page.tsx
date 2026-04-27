export default function ReviewPage({ params }: { params: { projectId: string } }) {
  return (
    <main className="container mx-auto p-8">
      <h1 className="text-2xl font-semibold mb-8">Review Queue</h1>
      <div className="rounded-xl border p-12 text-center text-muted-foreground">
        No tasks awaiting review.
      </div>
    </main>
  );
}
