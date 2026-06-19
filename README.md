# AI-Powered Website Audit Tool

A production-quality MVP that audits public websites across five categories:
**Performance**, **SEO**, **Accessibility**, **Security**, and **Functionality**.

---

## Tech Stack

| Layer    | Technology                          |
|----------|-------------------------------------|
| Frontend | React + TypeScript + Vite           |
| Backend  | Python + FastAPI + Uvicorn          |
| Audits   | Lighthouse CLI, Playwright, BS4     |
| Schema   | Pydantic v2                         |

---

## Project Structure

```
website-audit-tool/
├── frontend/          # React + TypeScript + Vite
├── backend/
│   └── app/
│       ├── main.py
│       ├── core/      # Config & logging
│       ├── routes/    # API endpoints
│       ├── schemas/   # Pydantic models
│       ├── audits/    # Audit modules
│       ├── services/  # Shared services
│       └── utils/     # Helpers
├── docs/
├── .gitignore
└── README.md
```

---

## Quick Start

### Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

---

## API Endpoints

| Method | Endpoint             | Description          |
|--------|----------------------|----------------------|
| GET    | /health              | Health check         |
| POST   | /audit               | Run full audit       |
| POST   | /audit/performance   | Performance only     |
| POST   | /audit/seo           | SEO only             |
| POST   | /audit/accessibility | Accessibility only   |
| POST   | /audit/security      | Security only        |
| POST   | /audit/functionality | Functionality only   |

Interactive docs: http://localhost:8000/docs

---

## Development Phases

- [x] Phase 1 — Project setup & health endpoint
- [ ] Phase 2 — Frontend ↔ Backend connection
- [ ] Phase 3 — Performance audit (Lighthouse)
- [ ] Phase 4 — SEO audit (BS4 + requests)
- [ ] Phase 5 — Accessibility audit (Playwright + axe-core)
- [ ] Phase 6 — Security audit (headers + SSL)
- [ ] Phase 7 — Functionality audit (Playwright)
- [ ] Final   — Dashboard + PDF export
