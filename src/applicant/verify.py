from concurrent.futures import ThreadPoolExecutor
from src.pdf_utils import bytes_to_base64
from src.client import extract_personal_info


def _normalize(value: str) -> str:
    return (value or "").strip().lower()


def _compare_field(field: str, form_value: str, extracted_value: str) -> dict:
    matched = bool(_normalize(extracted_value)) and _normalize(form_value) == _normalize(extracted_value)
    return {
        "field": field,
        "form_value": form_value or "",
        "document_value": extracted_value or "",
        "matched": matched,
    }


def verify_personal_info(files: list[tuple[str, bytes]], form_data: dict) -> dict:
    with ThreadPoolExecutor(max_workers=min(len(files), 8)) as executor:
        extractions = list(executor.map(
            lambda pair: extract_personal_info(bytes_to_base64(pair[1])), files
        ))

    per_document = []
    for (filename, _), extracted in zip(files, extractions):
        comparisons = [
            _compare_field("patient_name", form_data.get("patient_name", ""), extracted.get("patient_name", "")),
            _compare_field("date_of_birth", form_data.get("date_of_birth", ""), extracted.get("date_of_birth", "")),
            _compare_field("gender", form_data.get("gender", ""), extracted.get("gender", "")),
        ]
        per_document.append({
            "filename": filename,
            "comparisons": comparisons,
            "has_mismatch": any(not c["matched"] and c["document_value"] for c in comparisons),
        })

    return {"documents": per_document, "has_any_mismatch": any(d["has_mismatch"] for d in per_document)}