"""DuckDB-backed evidence store for collected compliance artifacts."""

import json

import duckdb


class EvidenceStore:
    """Thin wrapper around a DuckDB database for evidence persistence."""

    def __init__(self, db_path="':memory:'"):
        self.db_path = str(db_path)
        self.con = duckdb.connect(self.db_path)
        self._init_tables()

    def _init_tables(self):
        self.con.execute("CREATE SEQUENCE IF NOT EXISTS evidence_seq START 1")
        self.con.execute("""
            CREATE TABLE IF NOT EXISTS evidence (
                id              INTEGER PRIMARY KEY DEFAULT nextval('evidence_seq'),
                evidence_type   VARCHAR NOT NULL,
                source          VARCHAR NOT NULL,
                data_json       VARCHAR NOT NULL,
                sha256          VARCHAR(64) NOT NULL,
                collected_at    VARCHAR NOT NULL
            )
        """)
        self.con.execute("CREATE SEQUENCE IF NOT EXISTS analysis_seq START 1")
        self.con.execute("""
            CREATE TABLE IF NOT EXISTS analysis (
                id              INTEGER PRIMARY KEY DEFAULT nextval('analysis_seq'),
                framework       VARCHAR NOT NULL,
                control_id      VARCHAR NOT NULL,
                status          VARCHAR NOT NULL,
                finding         VARCHAR NOT NULL,
                recommendation  VARCHAR,
                analyzed_at     VARCHAR NOT NULL
            )
        """)

    def insert(self, evidence_type, source, data, sha256, collected_at):
        self.con.execute(
            "INSERT INTO evidence (evidence_type, source, data_json, sha256, collected_at) VALUES (?, ?, ?, ?, ?)",
            [
                evidence_type,
                source,
                json.dumps(data, default=str),
                sha256,
                collected_at,
            ],
        )

    def get_by_type(self, evidence_type):
        rows = self.con.execute(
            "SELECT data_json FROM evidence WHERE evidence_type = ?",
            [evidence_type],
        ).fetchall()
        return [json.loads(r[0]) for r in rows]

    def get_all_evidence(self):
        rows = self.con.execute(
            "SELECT id, evidence_type, source, data_json, sha256, collected_at FROM evidence ORDER BY id"
        ).fetchall()
        return [
            {
                "id": r[0],
                "evidence_type": r[1],
                "source": r[2],
                "data": json.loads(r[3]),
                "sha256": r[4],
                "collected_at": r[5],
            }
            for r in rows
        ]

    def count(self):
        return self.con.execute("SELECT COUNT(*) FROM evidence").fetchone()[0]

    def save_analysis(
        self, framework, control_id, status, finding, recommendation, analyzed_at
    ):
        self.con.execute(
            "INSERT INTO analysis (framework, control_id, status, finding, recommendation, analyzed_at) VALUES (?, ?, ?, ?, ?, ?)",
            [framework, control_id, status, finding, recommendation, analyzed_at],
        )

    def get_all_analysis(self):
        rows = self.con.execute(
            "SELECT id, framework, control_id, status, finding, recommendation, analyzed_at FROM analysis ORDER BY id"
        ).fetchall()
        return [
            {
                "id": r[0],
                "framework": r[1],
                "control_id": r[2],
                "status": r[3],
                "finding": r[4],
                "recommendation": r[5],
                "analyzed_at": r[6],
            }
            for r in rows
        ]

    def analysis_count(self):
        return self.con.execute("SELECT COUNT(*) FROM analysis").fetchone()[0]

    def close(self):
        self.con.close()
