# src/quality/validation.py
import re
import pandas as pd

EMAIL_REGEX = r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$"
VALID_CONDITIONS = ["Tiểu đường", "Huyết áp cao", "Tim mạch", "Khỏe mạnh"]
RAW_CSV = "data/raw/patients_raw.csv"
DTYPES = {"cccd": str, "so_dien_thoai": str}


def build_patient_expectation_suite():
    """Build a Great Expectations suite for patient data.

    Uses the GX 0.18 Fluent API. cccd is read as str so the 12-char length
    expectation is meaningful (otherwise pandas strips leading zeros to int).
    """
    import great_expectations as gx

    context = gx.get_context()
    suite = context.add_or_update_expectation_suite("patient_data_suite")

    df = pd.read_csv(RAW_CSV, dtype=DTYPES)
    validator = context.sources.pandas_default.read_dataframe(df)

    # 1. patient_id không được null
    validator.expect_column_values_to_not_be_null("patient_id")

    # 2. cccd phải có đúng 12 ký tự
    validator.expect_column_value_lengths_to_equal(column="cccd", value=12)

    # 3. ket_qua_xet_nghiem trong khoảng [0, 50]
    validator.expect_column_values_to_be_between(
        column="ket_qua_xet_nghiem", min_value=0, max_value=50
    )

    # 4. benh phải thuộc danh sách hợp lệ
    validator.expect_column_values_to_be_in_set(
        column="benh", value_set=VALID_CONDITIONS
    )

    # 5. email phải match regex
    validator.expect_column_values_to_match_regex(column="email", regex=EMAIL_REGEX)

    # 6. patient_id không được trùng
    validator.expect_column_values_to_be_unique(column="patient_id")

    validator.save_expectation_suite(discard_failed_expectations=False)
    return suite


def run_expectation_suite() -> dict:
    """Run the suite against the raw data and return a compact result summary."""
    validator = _build_validator()
    result = validator.validate()
    return {
        "success": bool(result.success),
        "evaluated": len(result.results),
        "failed": [r.expectation_config.expectation_type
                   for r in result.results if not r.success],
    }


def _build_validator():
    import great_expectations as gx
    context = gx.get_context()
    context.add_or_update_expectation_suite("patient_data_suite")
    df = pd.read_csv(RAW_CSV, dtype=DTYPES)
    validator = context.sources.pandas_default.read_dataframe(df)
    validator.expect_column_values_to_not_be_null("patient_id")
    validator.expect_column_value_lengths_to_equal(column="cccd", value=12)
    validator.expect_column_values_to_be_between(
        column="ket_qua_xet_nghiem", min_value=0, max_value=50)
    validator.expect_column_values_to_be_in_set(column="benh", value_set=VALID_CONDITIONS)
    validator.expect_column_values_to_match_regex(column="email", regex=EMAIL_REGEX)
    validator.expect_column_values_to_be_unique(column="patient_id")
    return validator


def validate_anonymized_data(filepath: str) -> dict:
    """Validate anonymized data WITHOUT a Great Expectations dependency.

    Returns: {"success": bool, "failed_checks": list, "stats": dict}
    """
    df = pd.read_csv(filepath, dtype=DTYPES)
    results = {
        "success": True,
        "failed_checks": [],
        "stats": {
            "total_rows": len(df),
            "columns": list(df.columns),
        },
    }

    def fail(msg):
        results["success"] = False
        results["failed_checks"].append(msg)

    original = pd.read_csv(RAW_CSV, dtype=DTYPES)

    # Check 1: no original CCCD value survives in the anonymized output
    orig_cccd = set(original["cccd"].astype(str))
    leaked = sorted(orig_cccd.intersection(set(df["cccd"].astype(str))))
    if leaked:
        fail(f"{len(leaked)} original CCCD value(s) leaked into anonymized output")

    # Check 2: critical columns have no nulls
    for col in ["patient_id", "benh"]:
        if col in df.columns and df[col].isnull().any():
            fail(f"null values found in '{col}'")

    # Check 3: row count preserved vs original
    if len(df) != len(original):
        fail(f"row count changed: {len(df)} != {len(original)}")

    # Check 4: emails are well-formed
    if "email" in df.columns:
        bad = [e for e in df["email"].astype(str) if not re.match(EMAIL_REGEX, e)]
        if bad:
            fail(f"{len(bad)} malformed email(s) in anonymized output")

    results["stats"]["checks_run"] = 4
    return results
