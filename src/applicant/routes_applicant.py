import json
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from src.applicant.verify import verify_personal_info
from src.casestore import create_case

router = APIRouter(prefix="/applicant", tags=["applicant"])


async def _read_pairs(files: list[UploadFile]) -> list[tuple[str, bytes]]:
    if not files:
        raise HTTPException(status_code=400, detail="No files provided.")
    pairs = []
    for f in files:
        if not (f.filename or "").lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail=f"{f.filename} is not a PDF.")
        pairs.append((f.filename, await f.read()))
    return pairs


def _parse_patient_data(patient_data: str) -> dict:
    try:
        return json.loads(patient_data)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="patient_data is not valid JSON.")


@router.post("/verify-identity")
async def verify_identity(
    files: list[UploadFile] = File(...),
    patient_data: str = Form(...),
):
    form_data = _parse_patient_data(patient_data)
    pairs = await _read_pairs(files)

    try:
        result = verify_personal_info(pairs, form_data)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))

    return result


@router.post("/submit-claim")
async def submit_claim(
    files: list[UploadFile] = File(...),
    patient_data: str = Form(...),
):
    form_data = _parse_patient_data(patient_data)
    pairs = await _read_pairs(files)

    try:
        verification = verify_personal_info(pairs, form_data)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))

    claim_ref = create_case(form_data, verification, pairs)
    return {"claim_ref": claim_ref, "verification": verification}