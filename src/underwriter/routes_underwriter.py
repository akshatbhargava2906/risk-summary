import json
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Body
from fastapi.responses import StreamingResponse, FileResponse
from src.pipeline import run
from src.client import generate_patient_summary
from src.casestore import list_cases, load_case, load_case_files, case_document_path

router = APIRouter(prefix="/underwriter", tags=["underwriter"])


def _run_stream(pairs: list[tuple[str, bytes]], questionnaire: dict) -> StreamingResponse:
    def stream():
        try:
            result = run(pairs, questionnaire)
            yield json.dumps(result["output"])
        except Exception as e:
            yield json.dumps({"error": str(e)})

    return StreamingResponse(stream(), media_type="application/json")


def _load_case_or_404(claim_ref: str) -> dict:
    try:
        return load_case(claim_ref)
    except (FileNotFoundError, ValueError):
        raise HTTPException(status_code=404, detail="Case not found.")


# ─ Generic (standalone testing, matches the original /analyse and /summarize-patient) ─

@router.post("/summarize-patient")
async def summarize_patient(patient_data: dict = Body(...)):
    try:
        summary = generate_patient_summary(patient_data)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))
    return {"summary": summary}


@router.post("/analyse")
async def analyse(
    files: list[UploadFile] = File(...),
    patient_data: str = Form(...),
):
    if not files:
        raise HTTPException(status_code=400, detail="No files provided.")
    try:
        questionnaire = json.loads(patient_data)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="patient_data is not valid JSON.")
    pairs = []
    for f in files:
        if not (f.filename or "").lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail=f"{f.filename} is not a PDF.")
        pairs.append((f.filename, await f.read()))

    return _run_stream(pairs, questionnaire)


# ─ Case-backed (reads what the applicant already submitted — no re-upload needed) ─

@router.get("/cases")
async def get_cases():
    return list_cases()


@router.get("/cases/{claim_ref}")
async def get_case(claim_ref: str):
    return _load_case_or_404(claim_ref)


@router.get("/cases/{claim_ref}/documents/{filename}")
async def get_case_document(claim_ref: str, filename: str):
    try:
        path = case_document_path(claim_ref, filename)
    except (FileNotFoundError, ValueError):
        raise HTTPException(status_code=404, detail="Document not found.")
    return FileResponse(path, media_type="application/pdf", filename=filename)


@router.post("/cases/{claim_ref}/summarize-patient")
async def summarize_case(claim_ref: str):
    case = _load_case_or_404(claim_ref)
    try:
        summary = generate_patient_summary(case["patient_data"])
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))
    return {"summary": summary}


@router.post("/cases/{claim_ref}/analyse")
async def analyse_case(claim_ref: str):
    case = _load_case_or_404(claim_ref)
    try:
        pairs = load_case_files(claim_ref)
    except (FileNotFoundError, ValueError):
        raise HTTPException(status_code=404, detail="Case documents not found.")

    return _run_stream(pairs, case["patient_data"])