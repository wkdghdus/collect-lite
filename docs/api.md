# API Reference

Base URL: `http://localhost:8000/api`

Interactive docs: `http://localhost:8000/docs`

## Projects

| Method | Path | Description |
|--------|------|-------------|
| POST | /projects | Create a project |
| GET | /projects | List all projects |
| GET | /projects/{project_id} | Get project detail |
| PATCH | /projects/{project_id} | Update project |

## Datasets

| Method | Path | Description |
|--------|------|-------------|
| POST | /projects/{project_id}/datasets | Upload dataset (CSV/JSONL) |
| GET | /projects/{project_id}/datasets | List datasets |
| GET | /datasets/{dataset_id}/errors | Get validation errors |

## Tasks

| Method | Path | Description |
|--------|------|-------------|
| POST | /projects/{project_id}/tasks/generate | Generate tasks from dataset |
| POST | /projects/{project_id}/tasks/suggest | Run model suggestions |
| GET | /tasks/next | Get next assigned task for annotator |
| GET | /tasks/{task_id} | Get task detail |

## Annotations

| Method | Path | Description |
|--------|------|-------------|
| POST | /tasks/{task_id}/annotations | Submit annotation |
| POST | /tasks/{task_id}/skip | Skip task |

## Reviews

| Method | Path | Description |
|--------|------|-------------|
| GET | /projects/{project_id}/review-queue | Get disagreement queue |
| POST | /reviews/{task_id}/resolve | Submit reviewer decision |

## Metrics

| Method | Path | Description |
|--------|------|-------------|
| GET | /projects/{project_id}/metrics | Get project metrics |

## Exports

| Method | Path | Description |
|--------|------|-------------|
| POST | /projects/{project_id}/exports | Create export |
| GET | /exports/{export_id} | Get export status |
| GET | /exports/{export_id}/download | Download export file |
