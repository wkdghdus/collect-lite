import { type ProjectResponse } from "@/lib/schemas/project";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

interface ProjectCardProps {
  project: ProjectResponse;
  onClick?: () => void;
}

const statusVariant: Record<string, "default" | "secondary" | "outline" | "destructive"> = {
  draft: "outline",
  active: "default",
  paused: "secondary",
  completed: "secondary",
};

export function ProjectCard({ project, onClick }: ProjectCardProps) {
  return (
    <Card className="cursor-pointer hover:shadow-md transition-shadow" onClick={onClick}>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base">{project.name}</CardTitle>
          <Badge variant={statusVariant[project.status] ?? "outline"}>{project.status}</Badge>
        </div>
      </CardHeader>
      <CardContent>
        <p className="text-sm text-muted-foreground line-clamp-2">{project.description ?? "No description."}</p>
        <p className="text-xs text-muted-foreground mt-3">{project.task_type}</p>
      </CardContent>
    </Card>
  );
}
