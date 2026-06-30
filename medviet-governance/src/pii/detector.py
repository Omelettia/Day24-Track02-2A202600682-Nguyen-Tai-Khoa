# src/pii/detector.py
"""Vietnamese-aware PII detection built on Microsoft Presidio.

Design notes (why this differs from the skeleton):
- `vi_core_news_lg` is NOT a real spaCy model. We use the official multilingual
  `xx_ent_wiki_sm` (NER: PER/LOC/ORG/MISC) mapped to lang_code "vi", with
  `en_core_web_sm` as a fallback.
- Presidio's predefined recognizers default to `supported_language="en"`, so under
  `language="vi"` they would NOT run. Every recognizer below is therefore
  registered explicitly for "vi" (including a "vi" EmailRecognizer).
- A custom PERSON recognizer backed by a Vietnamese surname deny-list makes name
  detection deterministic instead of depending on NER quality.
"""
from presidio_analyzer import AnalyzerEngine, PatternRecognizer, Pattern
from presidio_analyzer.predefined_recognizers import EmailRecognizer
from presidio_analyzer.nlp_engine import NlpEngineProvider

# Common Vietnamese surnames — verified to cover 100% of the Faker vi_VN names in
# the generated dataset. A name cell matches if any token is a surname.
VN_SURNAMES = [
    "Nguyễn", "Trần", "Lê", "Phạm", "Hoàng", "Huỳnh", "Phan", "Vũ", "Võ",
    "Đặng", "Bùi", "Đỗ", "Hồ", "Ngô", "Dương", "Lý", "Đào", "Đoàn", "Vương",
    "Trịnh", "Đinh", "Lâm", "Mai", "Trương", "Tô", "Tạ", "Lương", "Lưu",
    "Cao", "Hà", "Quách", "Thái", "Chu", "Châu", "Tăng", "Phùng", "Đàm",
    "Tống", "Kiều", "Hứa", "Tôn", "La",
]

DEFAULT_ENTITIES = ["PERSON", "EMAIL_ADDRESS", "VN_CCCD", "VN_PHONE"]


def build_vietnamese_analyzer() -> AnalyzerEngine:
    """Build an AnalyzerEngine with custom Vietnamese recognizers."""

    # --- TASK 2.2.1 --- CCCD: Vietnamese ID = exactly 12 digits
    cccd_pattern = Pattern(name="cccd_pattern", regex=r"\b\d{12}\b", score=0.9)
    cccd_recognizer = PatternRecognizer(
        supported_entity="VN_CCCD",
        patterns=[cccd_pattern],
        context=["cccd", "căn cước", "chứng minh", "cmnd"],
        supported_language="vi",
    )

    # --- TASK 2.2.2 --- Phone: 0 + [3,5,7,8,9] + 8 digits (10 digits total)
    phone_recognizer = PatternRecognizer(
        supported_entity="VN_PHONE",
        patterns=[Pattern(name="vn_phone", regex=r"\b0[35789]\d{8}\b", score=0.85)],
        context=["điện thoại", "sdt", "phone", "liên hệ"],
        supported_language="vi",
    )

    # Custom PERSON recognizer — deny-list of Vietnamese surnames guarantees name hits.
    person_recognizer = PatternRecognizer(
        supported_entity="PERSON",
        deny_list=VN_SURNAMES,
        context=["bệnh nhân", "bác sĩ", "ông", "bà", "anh", "chị"],
        supported_language="vi",
    )

    # Email recognizer registered for "vi" (the built-in default is "en"-only).
    email_recognizer = EmailRecognizer(supported_language="vi")

    # --- TASK 2.2.3 --- NLP engine. xx_ent_wiki_sm is multilingual; map it to "vi".
    try:
        provider = NlpEngineProvider(nlp_configuration={
            "nlp_engine_name": "spacy",
            "models": [{"lang_code": "vi", "model_name": "xx_ent_wiki_sm"}],
        })
        nlp_engine = provider.create_engine()
    except Exception:  # pragma: no cover - fallback when xx model unavailable
        provider = NlpEngineProvider(nlp_configuration={
            "nlp_engine_name": "spacy",
            "models": [{"lang_code": "vi", "model_name": "en_core_web_sm"}],
        })
        nlp_engine = provider.create_engine()

    # --- TASK 2.2.4 --- Build engine for "vi" and register every recognizer.
    analyzer = AnalyzerEngine(nlp_engine=nlp_engine, supported_languages=["vi"])
    analyzer.registry.add_recognizer(cccd_recognizer)
    analyzer.registry.add_recognizer(phone_recognizer)
    analyzer.registry.add_recognizer(person_recognizer)
    analyzer.registry.add_recognizer(email_recognizer)

    return analyzer


def detect_pii(text: str, analyzer: AnalyzerEngine) -> list:
    """Detect PII in Vietnamese text. Returns a list of RecognizerResult."""
    results = analyzer.analyze(
        text=str(text),
        language="vi",
        entities=DEFAULT_ENTITIES,
    )
    return results
