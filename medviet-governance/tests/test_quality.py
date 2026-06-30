# tests/test_quality.py
import pandas as pd
from src.quality.validation import validate_anonymized_data


def test_anonymized_data_passes():
    res = validate_anonymized_data("data/processed/patients_anonymized.csv")
    assert res["success"] is True
    assert res["failed_checks"] == []
    assert res["stats"]["total_rows"] == 200


def test_validator_flags_leaked_cccd(tmp_path):
    # Build a file that reuses an ORIGINAL cccd -> must be flagged as leaked.
    raw = pd.read_csv("data/raw/patients_raw.csv", dtype={"cccd": str, "so_dien_thoai": str})
    leaked = raw.copy()  # identical -> all CCCDs leaked
    p = tmp_path / "leaky.csv"
    leaked.to_csv(p, index=False)
    res = validate_anonymized_data(str(p))
    assert res["success"] is False
    assert any("CCCD" in c for c in res["failed_checks"])
