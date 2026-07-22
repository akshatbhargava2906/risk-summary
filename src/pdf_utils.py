import base64
from pathlib import Path

DOCUMENTS_DIR = Path(__file__).parent.parent / "Documents"

QUESTIONNAIRE_KEYWORDS = {"questionnaire", "form", "intake", "personal", "survey", "assessment", "screening", "checklist", "evaluation"}

def bytes_to_base64(data: bytes) -> str:
    return base64.b64encode(data).decode("utf-8")