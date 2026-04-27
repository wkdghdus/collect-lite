import Link from "next/link";

export default function ProjectsPage() {
  return (
    <main className="container mx-auto p-8">
      <div className="flex items-center justify-between mb-8">
        <h1 className="text-2xl font-semibold">Projects</h1>
        <button className="rounded-md bg-primary px-4 py-2 text-sm text-primary-foreground">
          New Project
        </button>
      </div>
      <div className="rounded-xl border p-12 text-center text-muted-foreground">
        No projects yet. Create your first annotation project to get started.
      </div>
    </main>
  );
}
