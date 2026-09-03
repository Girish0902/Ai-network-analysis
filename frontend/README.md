# AI-Assisted Criminal Investigation & Intelligence Platform — Frontend

React 18 + Vite 6 + Tailwind CSS v4 single-page application that integrates with the
FastAPI backend in `../backend`.

## Scope (Phase 0–1 integration)

- **Auth** — investigator signup, login, session restore via `/api/v1/auth/me`.
- **Dashboard** — create a case, list your cases (approved / pending / rejected),
  request access to an existing case.
- **Case workspace** — open the case, upload evidence, process it into a
  schema-versioned Unified Evidence payload, download the original file, and
  inspect extracted blocks/tables and processing metadata.
- **Admin console** — review and approve/reject pending case-access requests.
  Every decision is recorded in the tamper-evident audit trail.

## Setup

```powershell
cd frontend
npm install
npm run dev
```

The dev server proxies `/api` and `/health` to `http://127.0.0.1:8000` (see
`vite.config.js`). Start the backend first:

```powershell
cd ../backend
uvicorn app.main:app --reload --port 8000
```

## Commands

| Command | Purpose |
| :--- | :--- |
| `npm run dev` | Vite dev server on http://localhost:5173 |
| `npm run build` | Production build to `dist/` |
| `npm run preview` | Serve the production build |
| `npm run lint` | ESLint check |

## Demo flow

1. Sign up an investigator (`inv_ravi`), create a case.
2. Sign up a second investigator (`inv_sita`), request access to the case from the dashboard.
3. Sign in as `superadmin` (password from backend `.env` → `ADMIN_PASSWORD`) and approve the request.
4. Sign back in as `inv_sita` and open the case workspace.
5. Upload a CSV / PDF and click **Process** to see the extracted blocks and route metadata.