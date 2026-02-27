"""Tests for ClaudeGRC core functionality."""

import json


from claudegrc.evidence.store import EvidenceStore
from claudegrc.utils import hash_evidence, MOCKS_DIR


class TestEvidenceStore:
    def setup_method(self):
        self.store = EvidenceStore(":memory:")

    def teardown_method(self):
        self.store.close()

    def test_insert_and_count(self):
        self.store.insert(
            evidence_type="iam_policy",
            source="test",
            data={"policy": "test"},
            sha256=hash_evidence({"policy": "test"}),
            collected_at="2026-02-27T00:00:00Z",
        )
        assert self.store.count() == 1

    def test_get_by_type(self):
        self.store.insert(
            evidence_type="iam_policy",
            source="test",
            data={"name": "TestPolicy"},
            sha256="abc123",
            collected_at="2026-02-27T00:00:00Z",
        )
        self.store.insert(
            evidence_type="audit_log",
            source="test",
            data={"event": "InvokeModel"},
            sha256="def456",
            collected_at="2026-02-27T00:00:00Z",
        )
        iam = self.store.get_by_type("iam_policy")
        assert len(iam) == 1
        assert iam[0]["name"] == "TestPolicy"

    def test_save_and_get_analysis(self):
        self.store.save_analysis(
            framework="NIST AI RMF",
            control_id="GOVERN-1.1",
            status="PASS",
            finding="Policy exists.",
            recommendation="None",
            analyzed_at="2026-02-27T00:00:00Z",
        )
        results = self.store.get_all_analysis()
        assert len(results) == 1
        assert results[0]["status"] == "PASS"

    def test_get_all_evidence(self):
        self.store.insert(
            evidence_type="bedrock_models",
            source="mock/test.json",
            data={"model_id": "claude-3"},
            sha256="xyz",
            collected_at="2026-02-27T00:00:00Z",
        )
        all_ev = self.store.get_all_evidence()
        assert len(all_ev) == 1
        assert all_ev[0]["evidence_type"] == "bedrock_models"


class TestUtils:
    def test_hash_evidence_deterministic(self):
        data = {"key": "value", "num": 42}
        h1 = hash_evidence(data)
        h2 = hash_evidence(data)
        assert h1 == h2
        assert len(h1) == 64

    def test_hash_evidence_different(self):
        assert hash_evidence({"a": 1}) != hash_evidence({"a": 2})


class TestMockFiles:
    def test_mock_json_files_exist(self):
        expected = [
            "aws_iam_policies.json",
            "aws_bedrock_models.json",
            "aws_cloudtrail_ai_events.json",
        ]
        for f in expected:
            path = MOCKS_DIR / f
            assert path.exists(), f"Missing mock file: {f}"

    def test_mock_json_files_are_valid(self):
        for f in MOCKS_DIR.glob("*.json"):
            data = json.loads(f.read_text())
            assert isinstance(data, list), f"{f.name} should be a JSON array"
            assert len(data) > 0, f"{f.name} should not be empty"


class TestCollectMock:
    def test_collect_mock_loads_records(self):
        from claudegrc.collectors.aws import collect_mock

        store = EvidenceStore(":memory:")
        count = collect_mock(store)
        assert count > 0
        assert store.count() == count
        store.close()
