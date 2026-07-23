import json
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from src.applicant.verify import verify_personal_info

router = APIRouter(prefix="/applicant", tags=["applicant"])

@router.post("/verify-identity")
async def verify_identity(
    files: list[UploadFile] = File(...),
    patient_data: str = Form(...),
):
    if not files:
        raise HTTPException(status_code=400, detail="No files provided.")
    try:
        form_data = json.loads(patient_data)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="patient_data is not valid JSON.")
    pairs = []
    for f in files:
        if not (f.filename or "").lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail=f"{f.filename} is not a PDF.")
        pairs.append((f.filename, await f.read()))

    try:
        result = verify_personal_info(pairs, form_data)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))

    return result