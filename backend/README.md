# AI-Assisted Criminal Investigation & Intelligence Platform — Backend

**Phases 0–1.2: Security, Core Platform, Secure Ingestion & Document Router**

Production-grade FastAPI + SQLAlchemy 2.0 (typed Mapped) + Pydantic v2 foundation implementing:

- `FR-P0-01` Authentication (signup / login / JWT)
- `FR-P0-02` JWT + FastAPI dependency-injection pipeline (`get_current_user`, `require_admin`, `require_case_access`)
- `FR-P0-03` RBAC (Admin vs case-scanned investigator access)
- `FR-P0-04` Tamper-evident audit logging (SHA-256 hash-chained `AuditTrail`)
- `FR-P1-01` Secure ingestion (byte-signature MIME validation, ClamAV scan, SHA-256, immutable MinIO/local storage)
- `FR-P1-02` Document & Page Router (format detection, page-by-page text-presence, branch routing to Tabular / Native-PDF / Scanned)
- `FR-P1-08` Unified Evidence JSON (schema-versioned, paginated blocks with bbox + provenance)
- `FR-P1-09` `schema_version` on Unified Evidence payloads

Runs on **Python 3.12.1** (the single interpreter on this machine).

---

## 1. Project Layout

```
backend/
├── .env.example            # Copy to .env and fill values
├── docker-compose.yml      # PostgreSQL 16
├── requirements.txt
├── pyproject.toml          # pytest config
├── app/
│   ├── main.py             # FastAPI app + /health
│   ├── deps.py             # get_current_user, require_admin, require_case_access
│   ├── core/
│   │   ├── config.py       # Pydantic-settings
│   │   ├── database.py     # engine / SessionLocal / Base / get_db
│   │   ├── security.py     # bcrypt hashing + python-jose JWT
│   │   └── audit.py        # tamper-evident hash-chained audit writer
│   ├── models/entities.py  # User, Case, CaseAccess, AuditTrail
│   ├── schemas/            # Pydantic v2 request/response models
│   └── api/v1/
│       ├── router.py
│       └── routers/
│           ├── auth.py     # /auth/signup, /auth/login, /auth/me
│           ├── cases.py    # /cases/create, /cases/{id}/request-access, /cases/{id}/workspace
│           └── admin.py    # /admin/pending-requests, /admin/decide-access
├── scripts/init_db.py      # create tables + bootstrap ADMIN
└── tests/                  # pytest suite (SQLite in-memory)
```

---

## 2. Environment

```powershell
cd "C:\Users\ROG\Desktop\AI network analysis\backend"
Copy-Item .env.example .env
```

Generate a real secret and replace `SECRET_KEY` in `.env`:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

---

## 3. Install (Python 3.12.1)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

**Verify the interpreter in use:**

```powershell
python --version   # must print 3.12.1
```

---

## 4. Start PostgreSQL 16 (Docker) & Initialize DB

```powershell
docker compose up -d
python scripts/init_db.py
```

The script creates the tables and seeds the bootstrap `ADMIN` from `.env`
(`ADMIN_USERNAME` / `ADMIN_PASSWORD`).

---

## 5. Run the Server

```powershell
uvicorn app.main:app --reload --port 8000
```

Open the interactive API docs at **http://127.0.0.1:8000/docs**.

---

## 6. Verify — Step-by-Step (curl / PowerShell)

### 6.1 Health

```powershell
Invoke-RestMethod -Method Get http://127.0.0.1:8000/health
```

### 6.2 Signup an investigator

```powershell
$body = @{ username="inv_ravi"; email="ravi@police.in"; password="RaviPass2026!"; badge_number="2026-CID-01842" } | ConvertTo-Json
$signup = Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/v1/auth/signup -ContentType "application/json" -Body $body
$signup | ConvertTo-Json
```

### 6.3 Login and capture the JWT

```powershell
$login = Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/v1/auth/login -ContentType "application/json" -Body '{"username_or_email":"inv_ravi","password":"RaviPass2026!"}'
$token = $login.access_token
$Headers = @{ Authorization = "Bearer $token" }
```

### 6.4 Create a case (creator auto-granted access)

```powershell
$case = Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/v1/cases/create -Headers $Headers -ContentType "application/json" -Body '{"case_id":"CASE-2026-100","title":"Financial Fraud Ring","description":"Circular funds"}'
$case | ConvertTo-Json
```

### 6.5 Open your own workspace

```powershell
Invoke-RestMethod -Method Get -Uri http://127.0.0.1:8000/api/v1/cases/CASE-2026-100/workspace -Headers $Headers | ConvertTo-Json
```

### 6.6 Second investigator requests access

```powershell
$body2 = @{ username="inv_sita"; email="sita@police.in"; password="SitaPass2026!"; badge_number="2026-CCU-02917" } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/v1/auth/signup -ContentType "application/json" -Body $body2 | Out-Null

$login2 = Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/v1/auth/login -ContentType "application/json" -Body '{"username_or_email":"inv_sita","password":"SitaPass2026!"}'
$Headers2 = @{ Authorization = "Bearer $($login2.access_token)" }

Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/v1/cases/CASE-2026-100/request-access -Headers $Headers2 | ConvertTo-Json

# This must return 403 (no approved access yet)
try { Invoke-RestMethod -Method Get -Uri http://127.0.0.1:8000/api/v1/cases/CASE-2026-100/workspace -Headers $Headers2 } catch { $_.Exception.Response.StatusCode.value__ }
```

### 6.7 Admin approves the request

```powershell
$loginA = Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/v1/auth/login -ContentType "application/json" -Body '{"username_or_email":"superadmin","password":"<ADMIN_PASSWORD from .env>"}'
$HeadersA = @{ Authorization = "Bearer $($loginA.access_token)" }

Invoke-RestMethod -Method Get -Uri http://127.0.0.1:8000/api/v1/admin/pending-requests -Headers $HeadersA | ConvertTo-Json

Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/v1/admin/decide-access -Headers $HeadersA -ContentType "application/json" -Body '{"case_id":"CASE-2026-100","user_id":2,"decision":"APPROVE"}' | ConvertTo-Json

# Now the investigator can open the workspace
Invoke-RestMethod -Method Get -Uri http://127.0.0.1:8000/api/v1/cases/CASE-2026-100/workspace -Headers $Headers2 | ConvertTo-Json
```

### 6.8 Audit trail (tamper-evident)

Query the `audit_trails` table in PostgreSQL; every event carries a `tamper_hash` that chains to the previous event.

---

## 7. Run the automated test suite (SQLite in-memory, no Docker needed)

```powershell
cd "C:\Users\ROG\Desktop\AI network analysis\backend"
python -m pytest -v
```

Covers: signup validation, bcrypt+JWT login, RBAC, case creation, access-request flow,
admin approval/rejection, admin bypass, 401/403/404/409/422 paths, and audit-chain tamper detection.

---

## 8. Phase 1 Status

| Milestone | Scope | Status |
| :--- | :--- | :--- |
| Phase 1.1 | File validation, ClamAV scan, SHA-256 → MinIO/S3 | **Implemented** |
| Phase 1.2 | Content-based document & page router (pandas/PyMuPDF/visual canvas) | **Implemented** (Tabular + Native-PDF branches; Scanned routed to `OCR_PENDING`) |
| Phase 1.3 | Visual preprocessing (deskew/denoise/CLAHE) + layout segmentation | Next |
| Phase 1.4 | Multi-engine OCR/HTR (PaddleOCR/Surya + Indic HTR + table parser) | Next |
| Phase 1.5 | Unicode NFC/ZWJ-ZWNJ normalization + Unified Evidence JSON serialization | Next |

## 9. Phase 1.1 / 1.2 Storage & Processing Notes

- `STORAGE_BACKEND=local` writes immutable evidence under `LOCAL_STORAGE_ROOT/<bucket>/cases/{case_id}/{sha256}/{filename}`. Set `STORAGE_BACKEND=minio` for S3-compatible object storage (presigned download URL available).
- Evidence is routed on `POST /api/v1/cases/{case_id}/evidence/{document_id}/process`:
  - `route=TABULAR` — xlsx/xls/csv parsed into structured tables (`structured_tables[]`).
  - `route=NATIVE_DIGITAL_PDF` — PyMuPDF text blocks with bbox emitted into `blocks[]`.
  - `route=SCANNED_VISUAL_PDF` — no extractable text; persisted as an `OCR_PENDING` job (Phase 1.3/1.4 will backfill via OCR/HTR).
- Unified Evidence JSON carries `schema_version` (currently `1.0.0`) for future-safe migrations of stored payloads.

We wait for your Phase 1.1/1.2 verification before starting Phase 1.3.