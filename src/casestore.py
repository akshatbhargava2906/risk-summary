import json
import re
import time
from pathlib import Path

CASES_DIR = Path(".cases")

_SAFE_COMPONENT = re.compile(r"^[A-Za-z0-9_.\-]+$")


def _is_safe_component(value: str) -> bool:
    return bool(value) and ".." not in value and bool(_SAFE_COMPONENT.match(value))


def _case_dir(claim_ref: str) -> Path:
    if not _is_safe_component(claim_ref):
        raise ValueError(f"Invalid claim reference: {claim_ref!r}")
    return CASES_DIR / claim_ref


def create_case(patient_data: dict, verification: dict, files: list[tuple[str, bytes]]) -> str:
    claim_ref = "CLM-" + str(int(time.time() * 1000))[-10:]
    case_dir = _case_dir(claim_ref)
    docs_dir = case_dir / "documents"
    docs_dir.mkdir(parents=True, exist_ok=True)

    filenames = []
    for filename, data in files:
        (docs_dir / filename).write_bytes(data)
        filenames.append(filename)

    meta = {
        "claim_ref": claim_ref,
        "submitted_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "patient_data": patient_data,
        "verification": verification,
        "documents": filenames,
        "status": "submitted",
    }
    (case_dir / "meta.json").write_text(json.dumps(meta, indent=2))
    return claim_ref


def load_case(claim_ref: str) -> dict:
    meta_path = _case_dir(claim_ref) / "meta.json"
    if not meta_path.exists():
        raise FileNotFoundError(f"No case found for {claim_ref}")
    return json.loads(meta_path.read_text())


def load_case_files(claim_ref: str) -> list[tuple[str, bytes]]:
    case_dir = _case_dir(claim_ref)
    meta = load_case(claim_ref)
    docs_dir = case_dir / "documents"
    return [(name, (docs_dir / name).read_bytes()) for name in meta["documents"]]


def case_document_path(claim_ref: str, filename: str) -> Path:
    if not _is_safe_component(filename):
        raise ValueError(f"Invalid document filename: {filename!r}")
    path = _case_dir(claim_ref) / "documents" / filename
    if not path.exists():
        raise FileNotFoundError(f"No document {filename!r} for case {claim_ref}")
    return path


def list_cases() -> list[dict]:
    if not CASES_DIR.exists():
        return []
    cases = []
    for case_dir in sorted(CASES_DIR.iterdir(), reverse=True):
        meta_path = case_dir / "meta.json"
        if meta_path.exists():
            cases.append(json.loads(meta_path.read_text()))
    return cases