# Medical Risk Analyzer API

An AI-powered REST API that extracts health indicators from medical PDFs,
scores patient risk (0–100), and produces a clinical summary for insurance
underwriting — via Claude on SAP AI Core.

---

## API Endpoints

| Method | URL        | Description                        |
|--------|------------|------------------------------------|
| GET    | `/health`  | Liveness check                     |
| POST   | `/analyse` | Run risk analysis on uploaded PDFs |
| GET    | `/docs`    | Interactive Swagger UI             |

### POST `/analyse`

Accepts one or more PDF files as multipart form-data. Accepts any combination
of patient questionnaires and medical reports (blood reports, ECG, chest X-ray,
etc.). Document type is classified automatically from the filename — files
containing `questionnaire`, `form`, or `intake` in the name are routed to the
questionnaire extractor; all others are treated as medical reports.

**Request**
```
Content-Type: multipart/form-data
Field name: files  (repeat for each PDF)
```

**Response**
```json
{
  "patient": {
    "name": "John Doe",
    "age": "54",
    "gender": "Male",
    "location": "Singapore"
  },
  "insurance": {
    "current_coverage": "Life + Critical Illness",
    "coverage_amount": "SGD 500,000",
    "previous_claims": "1 claim (2021)",
    "smoking_status": "Former Smoker",
    "pack_years": "15",
    "family_history": ["Hypertension", "Type 2 Diabetes"]
  },
  "risk_assessment": {
    "score": 82,
    "tier": "Risk",
    "indicator_points": 68,
    "questionnaire_points": 14,
    "total_indicators": 14,
    "flagged_count": 8
  },
  "summary": "Patient presents with multiple cardiovascular risk factors...",
  "flagged_indicators": [
    {
      "source": "Blood Report",
      "name": "LDL Cholesterol",
      "value": "4.8",
      "unit": "mmol/L",
      "reference_range": "< 3.4 mmol/L",
      "status": "critical",
      "note": "Significantly elevated; statin therapy indicated"
    }
  ]
}
```

---

## Risk Scoring

Scoring is fully deterministic — no LLM involved.

### Clinical indicators (from medical reports)

| Status   | Points each | Cap    |
|----------|-------------|--------|
| abnormal | +8          | max 40 |
| critical | +20         | max 60 |

### Questionnaire adjustments (from patient intake form)

| Factor                       | Points |
|------------------------------|--------|
| Current smoker               | +10    |
| Former smoker                | +5     |
| 2+ family history conditions | +8     |
| Previous insurance claims    | +5     |

Combined total is capped at 100.

### Risk tiers

| Score    | Tier   |
|----------|--------|
| 0 – 49   | Normal |
| 50 – 74  | High   |
| 75 – 100 | Risk   |

---

## Project Structure

```
risk-analysis-usecase/
├── api.py                  # FastAPI entry point
├── manifest.yml            # CF deployment config
├── Procfile
├── runtime.txt
├── requirements.txt
├── .env.example
└── src/
    ├── pipeline.py         # Core run() — shared by API
    ├── client.py           # Claude via SAP AI Core (OAuth2)
    ├── questionnaire.py    # Patient intake form extraction
    ├── risk_scorer.py      # Scoring and tier logic
    ├── pdf_utils.py        # PDF utilities and doc classification
    └── cache.py            # JSON cache (.cache/{patient_id}/)
```

---

## Local Setup

```bash
git clone <repo-url>
cd risk-analysis-usecase
pip install -r requirements.txt
cp .env.example .env        # fill in SAP AI Core credentials
uvicorn api:app --reload
```

## Environment Variables

```
AUTH_URL=
CLIENT_ID=
CLIENT_SECRET=
DEPLOYMENT_ID=
```

---

## Caching

Extracted indicators and questionnaire data are cached as JSON under
`.cache/{patient_id}/` after the first run. Subsequent requests for the
same patient load from cache, skipping the Claude extraction calls entirely.
The patient ID is derived from the first uploaded filename stem.

Note: the cache is ephemeral on Cloud Foundry (cleared on restart).
Both `.cache/` and `.chroma/` are excluded from version control via `.gitignore`.

---
