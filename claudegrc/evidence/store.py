import duckdb
import json


class EvidenceStore:
    def __init__(self):
        self.con = duckdb.connect("evidence.db")

    def save_evidence(self, evidence: dict):
        self.con.execute(
            "CREATE TABLE IF NOT EXISTS evidence (key VARCHAR, value JSON)"
        )
        for k, v in evidence.items():
            self.con.execute("INSERT INTO evidence VALUES (?, ?)", (k, json.dumps(v)))

    def load_evidence(self) -> dict:
        rows = self.con.execute("SELECT key, value FROM evidence").fetchall()
        return {r[0]: json.loads(r[1]) for r in rows}

    def save_analysis(self, analysis: dict):
        # Simple for now - expand later
        pass

    def load_analysis(self) -> dict:
        return {}
