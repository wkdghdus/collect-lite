export default function AnnotatePage() {
  return (
    <main className="container mx-auto p-8 max-w-4xl">
      <h1 className="text-2xl font-semibold mb-2">Annotation Workbench</h1>
      <p className="text-sm text-muted-foreground mb-8">Complete assigned tasks below.</p>
      <div className="rounded-xl border p-12 text-center text-muted-foreground">
        No tasks assigned. Check back soon.
      </div>
    </main>
  );
}
