# src/pii/anonymizer.py
import random
import pandas as pd
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig
from faker import Faker
from .detector import build_vietnamese_analyzer, detect_pii

fake = Faker("vi_VN")


class MedVietAnonymizer:

    def __init__(self):
        self.analyzer = build_vietnamese_analyzer()
        self.anonymizer = AnonymizerEngine()

    @staticmethod
    def _fake_cccd() -> str:
        """12-digit fake Vietnamese ID."""
        return "".join(str(random.randint(0, 9)) for _ in range(12))

    @staticmethod
    def _fake_phone() -> str:
        """Fake Vietnamese mobile: 0 + [3,5,7,8,9] + 8 digits."""
        return "0" + str(random.choice([3, 5, 7, 8, 9])) + \
            "".join(str(random.randint(0, 9)) for _ in range(8))

    def anonymize_text(self, text: str, strategy: str = "replace") -> str:
        """Anonymize free text using the chosen strategy.

        Strategies:
        - "mask"     : replace leading characters with '*'
        - "replace"  : substitute realistic fake data (Faker)
        - "hash"     : SHA-256 one-way hash
        """
        results = detect_pii(text, self.analyzer)
        if not results:
            return text

        entities = ["PERSON", "EMAIL_ADDRESS", "VN_CCCD", "VN_PHONE"]

        if strategy == "replace":
            operators = {
                "PERSON": OperatorConfig("replace", {"new_value": fake.name()}),
                "EMAIL_ADDRESS": OperatorConfig("replace", {"new_value": fake.email()}),
                "VN_CCCD": OperatorConfig("replace", {"new_value": self._fake_cccd()}),
                "VN_PHONE": OperatorConfig("replace", {"new_value": self._fake_phone()}),
            }
        elif strategy == "mask":
            operators = {
                e: OperatorConfig("mask", {
                    "masking_char": "*",
                    "chars_to_mask": 4,
                    "from_end": False,
                }) for e in entities
            }
        elif strategy == "hash":
            operators = {e: OperatorConfig("hash", {"hash_type": "sha256"}) for e in entities}
        else:
            operators = {"DEFAULT": OperatorConfig("replace", {"new_value": "<REDACTED>"})}

        anonymized = self.anonymizer.anonymize(
            text=text,
            analyzer_results=results,
            operators=operators,
        )
        return anonymized.text

    def anonymize_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Anonymize an entire DataFrame.

        - Text PII (ho_ten, dia_chi, email, bac_si_phu_trach): replaced with fake data
        - cccd, so_dien_thoai: replaced directly with fake values
        - benh, ket_qua_xet_nghiem: PRESERVED (needed for model training)
        - patient_id, ngay_sinh, ngay_kham: PRESERVED (pseudonymous / low-risk)

        Replacing PII columns wholesale guarantees the original value cannot
        survive in the output (deterministic anonymization).
        """
        df_anon = df.copy()
        n = len(df_anon)

        if "ho_ten" in df_anon.columns:
            df_anon["ho_ten"] = [fake.name() for _ in range(n)]
        if "email" in df_anon.columns:
            df_anon["email"] = [fake.email() for _ in range(n)]
        if "dia_chi" in df_anon.columns:
            df_anon["dia_chi"] = [fake.address().replace("\n", ", ") for _ in range(n)]
        if "bac_si_phu_trach" in df_anon.columns:
            df_anon["bac_si_phu_trach"] = [fake.name() for _ in range(n)]
        if "cccd" in df_anon.columns:
            df_anon["cccd"] = [self._fake_cccd() for _ in range(n)]
        if "so_dien_thoai" in df_anon.columns:
            df_anon["so_dien_thoai"] = [self._fake_phone() for _ in range(n)]

        return df_anon

    def calculate_detection_rate(self,
                                 original_df: pd.DataFrame,
                                 pii_columns: list) -> float:
        """Percent of PII cells where detect_pii() finds >= 1 entity. Target > 95%."""
        total = 0
        detected = 0

        for col in pii_columns:
            for value in original_df[col].astype(str):
                total += 1
                results = detect_pii(value, self.analyzer)
                if len(results) > 0:
                    detected += 1

        return detected / total if total > 0 else 0.0
