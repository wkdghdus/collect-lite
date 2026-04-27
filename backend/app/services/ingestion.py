import hashlib
import json
from io import BytesIO

import pandas as pd


def compute_source_hash(payload: dict) -> str:
    serialized = json.dumps(payload, sort_keys=True)
    return hashlib.sha256(serialized.encode()).hexdigest()


def parse_jsonl(content: bytes) -> list[dict]:
    rows = []
    for line in content.decode().splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def parse_csv(content: bytes) -> list[dict]:
    df = pd.read_csv(BytesIO(content), dtype=str)
    df = df.where(pd.notnull(df), None)
    return df.to_dict(orient="records")


def parse_upload(filename: str, content: bytes) -> list[dict]:
    if filename.endswith(".jsonl"):
        return parse_jsonl(content)
    if filename.endswith(".csv"):
        return parse_csv(content)
    raise ValueError(f"Unsupported file type: {filename}")


REQUIRED_POINTWISE = ("query", "candidate_document")
REQUIRED_PAIRWISE = ("query", "candidate_a", "candidate_b")


def _filled(value) -> bool:
    return value is not None and str(value).strip() != ""


def normalize_rows(rows: list[dict]) -> tuple[list[dict], list[dict]]:
    """Translate parsed rows into canonical pointwise examples.

    Pairwise rows (with both candidate_a and candidate_b) expand into two
    pointwise examples with generated document_ids row_<idx>_a and row_<idx>_b.
    Pointwise rows fall back to row_<idx> when document_id is absent.

    Returns (examples, errors). Each example dict has query, candidate_document,
    document_id, metadata. Each error dict has row (input index) and missing.
    """
    examples: list[dict] = []
    errors: list[dict] = []
    for idx, row in enumerate(rows):
        is_pairwise = "candidate_a" in row and "candidate_b" in row
        required = REQUIRED_PAIRWISE if is_pairwise else REQUIRED_POINTWISE
        missing = [field for field in required if not _filled(row.get(field))]
        if missing:
            errors.append({"row": idx, "missing": missing})
            continue
        metadata = row.get("metadata")
        if is_pairwise:
            for suffix, candidate_field in (("a", "candidate_a"), ("b", "candidate_b")):
                examples.append(
                    {
                        "query": row["query"],
                        "candidate_document": row[candidate_field],
                        "document_id": f"row_{idx}_{suffix}",
                        "metadata": metadata,
                    }
                )
        else:
            document_id = row["document_id"] if _filled(row.get("document_id")) else f"row_{idx}"
            examples.append(
                {
                    "query": row["query"],
                    "candidate_document": row["candidate_document"],
                    "document_id": document_id,
                    "metadata": metadata,
                }
            )
    return examples, errors


def example_source_hash(example: dict) -> str:
    """Hash query + candidate_document + document_id for idempotency."""
    return compute_source_hash(
        {
            "query": example["query"],
            "candidate_document": example["candidate_document"],
            "document_id": example["document_id"],
        }
    )
