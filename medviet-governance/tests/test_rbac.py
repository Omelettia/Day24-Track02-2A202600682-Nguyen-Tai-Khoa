# tests/test_rbac.py
import warnings
from fastapi.testclient import TestClient
from src.api.main import app

warnings.filterwarnings("ignore")

client = TestClient(app)


def _h(token):
    return {"Authorization": f"Bearer {token}"}


# --- authentication ---
def test_missing_token_401():
    assert client.get("/api/patients/raw").status_code == 401


def test_invalid_token_401():
    assert client.get("/api/patients/raw", headers=_h("token-nope")).status_code == 401


# --- raw PII (admin only) ---
def test_admin_reads_raw():
    r = client.get("/api/patients/raw", headers=_h("token-alice"))
    assert r.status_code == 200
    assert len(r.json()) == 10


def test_ml_engineer_denied_raw():
    assert client.get("/api/patients/raw", headers=_h("token-bob")).status_code == 403


def test_analyst_denied_raw():
    assert client.get("/api/patients/raw", headers=_h("token-carol")).status_code == 403


def test_intern_denied_raw():
    assert client.get("/api/patients/raw", headers=_h("token-dave")).status_code == 403


# --- anonymized data (ml_engineer + admin) ---
def test_ml_engineer_reads_anonymized():
    assert client.get("/api/patients/anonymized", headers=_h("token-bob")).status_code == 200


def test_analyst_denied_anonymized():
    assert client.get("/api/patients/anonymized", headers=_h("token-carol")).status_code == 403


# --- aggregated metrics (data_analyst + ml_engineer + admin) ---
def test_analyst_reads_metrics():
    r = client.get("/api/metrics/aggregated", headers=_h("token-carol"))
    assert r.status_code == 200
    assert "by_condition" in r.json()


def test_ml_engineer_reads_metrics():
    assert client.get("/api/metrics/aggregated", headers=_h("token-bob")).status_code == 200


# --- delete (admin only) ---
def test_ml_engineer_denied_delete():
    assert client.delete("/api/patients/abc123", headers=_h("token-bob")).status_code == 403


def test_admin_deletes():
    r = client.delete("/api/patients/abc123", headers=_h("token-alice"))
    assert r.status_code == 200
    assert r.json()["deleted"] == "abc123"


def test_health_ok():
    assert client.get("/health").status_code == 200
