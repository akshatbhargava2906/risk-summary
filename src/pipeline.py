from pathlib import Path
from src.pdf_utils import bytes_to_base64
from src.client import extract_indicators, generate_analysis
from src.risk_scorer import score_report
from concurrent.futures import ThreadPoolExecutor
from src.cache import save_cache, load_cache


def _extract_summary(analysis_text: str) -> str:
    if not analysis_text:
        return ""
    lines = analysis_text.splitlines()
    in_summary = False
    summary_lines = []
    for line in lines:
        clean = line.strip().lstrip("#*_ ").rstrip(":").upper()
        if clean == "SUMMARY":
            in_summary = True
            continue
        if in_summary:
            if clean in ("FLAGGED INDICATORS", "RECOMMENDATIONS"):
                break
            summary_lines.append(line.strip())
    return " ".join(l for l in summary_lines if l).strip()


def _build_output(result: dict, questionnaire: dict, analysis_text: str, docs_processed: list) -> dict:
    insurance = questionnaire.get("insurance", {})
    smoking = questionnaire.get("smoking", {})
    return {
        "patient": {
            "name": questionnaire.get("patient_name", ""),
            "age": questionnaire.get("age", ""),
            "gender": questionnaire.get("gender", ""),
            "location": questionnaire.get("location", ""),
        },
        "insurance": {
            "current_coverage": insurance.get("current_coverage", ""),
            "coverage_amount": insurance.get("coverage_amount", ""),
            "previous_claims": insurance.get("previous_claims", ""),
            "smoking_status": smoking.get("status", ""),
            "pack_years": smoking.get("pack_years", ""),
            "family_history": questionnaire.get("family_history", []),
        },
        "risk_assessment": {
            "score": result["score"],
            "tier": result["tier"],
            "indicator_points": result["indicator_pts"],
            "questionnaire_points": result["questionnaire_pts"],
            "total_indicators": result["total"],
            "flagged_count": result["flagged_count"],
        },
        "summary": _extract_summary(analysis_text),
        "flagged_indicators": [
            {
                "name": ind.get("name", ""),
                "value": ind.get("value", ""),
                "unit": ind.get("unit", ""),
                "reference_range": ind.get("reference_range", ""),
                "status": ind.get("status", ""),
                "note": ind.get("note", ""),
                "source": ind.get("doc_type", ""),
            }
            for ind in result.get("flagged", [])
        ],
        "docs_processed": docs_processed,
    }


def run(files: list[tuple[str, bytes]], questionnaire: dict) -> dict:
    patient_id = Path(files[0][0]).stem.replace(" ", "_").lower()

    cached = load_cache(patient_id)
    if cached:
        all_indicators = cached
        docs_processed = ["cache"]
    else:
        with ThreadPoolExecutor(max_workers=min(len(files), 8)) as executor:
            extractions = list(executor.map(
                lambda pair: extract_indicators(bytes_to_base64(pair[1])), files
            ))

        all_indicators = []
        docs_processed = []
        for (filename, _), extraction in zip(files, extractions):
            indicators = extraction.get("indicators", [])
            for ind in indicators:
                ind["doc_type"] = extraction.get("doc_type", "medical")
            all_indicators.extend(indicators)
            docs_processed.append(filename)
        save_cache(patient_id, all_indicators)

    result = score_report(all_indicators, questionnaire)
    analysis_text = generate_analysis(result["score"], result["tier"], result["flagged"], questionnaire)

    return {
        "output": _build_output(result, questionnaire, analysis_text, docs_processed),
        "result": result,
        "questionnaire": questionnaire,
        "analysis_text": analysis_text,
        "docs_processed": docs_processed,
    }