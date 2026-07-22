import json
from pathlib import Path

CACHE_PATH = Path(".cache")

def save_cache(patient_id: str, indicators: list):
    folder = CACHE_PATH / patient_id
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "indicators.json").write_text(json.dumps(indicators))

def load_cache(patient_id: str) -> list | None:
    folder = CACHE_PATH / patient_id
    ind_file = folder / "indicators.json"
    if not ind_file.exists():
        return None
    return json.loads(ind_file.read_text())