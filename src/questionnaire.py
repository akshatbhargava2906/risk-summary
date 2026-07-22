from src.client import _invoke_claude
import json
from json_repair import repair_json

SMOKING_RISK = {
    "current": 10,
    "former": 5,
    "never": 0,
}

FAMILY_HISTORY_THRESHOLD = 2
FAMILY_HISTORY_RISK = 8
PREVIOUS_CLAIMS_RISK = 5


def extract_questionnaire(pdf_b64: str) -> dict:
    system = """You are a patient intake form extraction assistant.
Extract patient details from the questionnaire PDF.
Return ONLY valid JSON — no explanation, no markdown fences:
{
  "patient_name": "string",
  "age": "string",
  "gender": "string",
  "location": "string",
  "smoking": {
    "status": "never|former|current",
    "pack_years": "string"
  },
  "family_history": ["condition1", "condition2"],
  "insurance": {
    "current_coverage": "string",
    "previous_claims": "string",
    "coverage_amount": "string"
  }
}
If a field is not found in the document, use an empty string or empty list."""

    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 2048,
        "system": system,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "document",
                        "source": {
                            "type": "base64",
                            "media_type": "application/pdf",
                            "data": pdf_b64,
                        },
                    },
                    {"type": "text", "text": "Extract the patient questionnaire details and return the JSON."},
                ],
            }
        ],
    }

    raw = _invoke_claude(body)["content"][0]["text"].strip()
    raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()

    start = raw.find("{")
    end = raw.rfind("}") + 1
    if start == -1 or end == 0:
        return _empty_questionnaire()
    raw = raw[start:end]

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return json.loads(repair_json(raw))


def questionnaire_risk_points(q: dict) -> int:
    if not q:
        return 0

    points = 0

    smoking_status = q.get("smoking", {}).get("status", "never").lower()
    points += SMOKING_RISK.get(smoking_status, 0)

    family_history = q.get("family_history", [])
    if len(family_history) >= FAMILY_HISTORY_THRESHOLD:
        points += FAMILY_HISTORY_RISK

    previous_claims = q.get("insurance", {}).get("previous_claims", "").lower()
    if previous_claims and previous_claims not in ("none", "no", "nil", ""):
        points += PREVIOUS_CLAIMS_RISK

    return points


def _empty_questionnaire() -> dict:
    return {
        "patient_name": "",
        "age": "",
        "gender": "",
        "location": "",
        "smoking": {"status": "never", "pack_years": ""},
        "family_history": [],
        "insurance": {
            "current_coverage": "",
            "previous_claims": "",
            "coverage_amount": "",
        },
    }