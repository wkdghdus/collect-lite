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
    df = pd.read_csv(BytesIO(content))
    return df.to_dict(orient="records")


def parse_upload(filename: str, content: bytes) -> list[dict]:
    if filename.endswith(".jsonl"):
        return parse_jsonl(content)
    if filename.endswith(".csv"):
        return parse_csv(content)
    raise ValueError(f"Unsupported file type: {filename}")
