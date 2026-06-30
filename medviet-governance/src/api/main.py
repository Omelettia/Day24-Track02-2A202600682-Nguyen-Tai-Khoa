# src/api/main.py
from fastapi import FastAPI, Depends
from fastapi.responses import JSONResponse
import pandas as pd
from src.access.rbac import get_current_user, require_permission
from src.pii.anonymizer import MedVietAnonymizer

app = FastAPI(title="MedViet Data API", version="1.0.0")
anonymizer = MedVietAnonymizer()

RAW_CSV = "data/raw/patients_raw.csv"
# Read identifier columns as str so leading zeros (phones, 0-prefixed CCCDs) survive.
_DTYPES = {"cccd": str, "so_dien_thoai": str}


def _load_raw() -> pd.DataFrame:
    return pd.read_csv(RAW_CSV, dtype=_DTYPES)


# --- ENDPOINT 1 --- raw PII: admin only
@app.get("/api/patients/raw")
@require_permission(resource="patient_data", action="read")
async def get_raw_patients(current_user: dict = Depends(get_current_user)):
    df = _load_raw().head(10)
    return JSONResponse(content=df.to_dict(orient="records"))


# --- ENDPOINT 2 --- anonymized data: ml_engineer + admin
@app.get("/api/patients/anonymized")
@require_permission(resource="training_data", action="read")
async def get_anonymized_patients(current_user: dict = Depends(get_current_user)):
    df = _load_raw().head(10)
    df_anon = anonymizer.anonymize_dataframe(df)
    return JSONResponse(content=df_anon.to_dict(orient="records"))


# --- ENDPOINT 3 --- aggregated metrics: data_analyst + ml_engineer + admin
@app.get("/api/metrics/aggregated")
@require_permission(resource="aggregated_metrics", action="read")
async def get_aggregated_metrics(current_user: dict = Depends(get_current_user)):
    df = _load_raw()
    by_condition = {str(k): int(v) for k, v in df["benh"].value_counts().items()}
    return {
        "total_patients": int(len(df)),
        "by_condition": by_condition,
        "avg_test_result": round(float(df["ket_qua_xet_nghiem"].mean()), 2),
    }


# --- ENDPOINT 4 --- delete a patient: admin only
@app.delete("/api/patients/{patient_id}")
@require_permission(resource="patient_data", action="delete")
async def delete_patient(patient_id: str, current_user: dict = Depends(get_current_user)):
    return {"deleted": patient_id, "by": current_user["username"]}


@app.get("/health")
async def health():
    return {"status": "ok", "service": "MedViet Data API"}
