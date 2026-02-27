"""AWS evidence collectors — mock and (future) live modes."""

import json
import os

from claudegrc.utils import MOCKS_DIR, hash_evidence, now_iso


# Map mock filenames to evidence types
_MOCK_FILE_MAP = {
    "aws_iam_policies.json": "iam_policy",
    "aws_bedrock_models.json": "bedrock_models",
    "aws_cloudtrail_ai_events.json": "audit_log",
}


def collect_mock(store) -> int:
    """Load all mock JSON fixtures into the evidence store. Returns record count."""
    count = 0
    for filename, evidence_type in _MOCK_FILE_MAP.items():
        path = MOCKS_DIR / filename
        if not path.exists():
            continue
        records = json.loads(path.read_text())
        for record in records:
            store.insert(
                evidence_type=evidence_type,
                source=f"mock/{filename}",
                data=record,
                sha256=hash_evidence(record),
                collected_at=now_iso(),
            )
            count += 1
    return count


def collect_aws_evidence(profile=None, mock=False):
    """Collect evidence from AWS (mock mode for now)."""
    if mock or os.getenv("MOCK_MODE") == "true":
        evidence = {}
        for file in os.listdir(str(MOCKS_DIR)):
            if file.endswith(".json"):
                key = file.split(".")[0]
                with open(MOCKS_DIR / file, "r") as f:
                    evidence[key] = json.load(f)
        return evidence
    # Real AWS code would go here later
    return {}
