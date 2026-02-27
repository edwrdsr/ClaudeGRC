"""Shared utilities for ClaudeGRC."""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MOCKS_DIR = PROJECT_ROOT / "mocks"
FRAMEWORKS_DIR = PROJECT_ROOT / "frameworks"
DB_PATH = PROJECT_ROOT / "claudegrc.duckdb"
REPORTS_DIR = PROJECT_ROOT / "output"


def hash_evidence(data: dict | list | str) -> str:
    """Return a SHA-256 hex digest for an evidence payload."""
    raw = json.dumps(data, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode()).hexdigest()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
