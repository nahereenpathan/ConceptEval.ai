# Concept-Aware Code Evaluation Using NLP and AST Analysis

A production-ready SaaS platform for automated programming assessment that evaluates both **functional correctness** (via sandboxed test execution) and **conceptual compliance** (via Python Abstract Syntax Tree analysis and NLP-driven intent extraction).

---

## Key Capabilities

1. **Dual-Track Evaluation**: Distinguishes between solutions that simply match outputs and solutions that actually use the required algorithmic constructs (e.g. loops, recursion, list comprehensions, exception handling).
2. **Deterministic, Evidence-Based Scoring**: Rubrics assign weighted points to functional behavior vs concept compliance with zero LLM score hallucinations.
3. **Isolated Code Runner**: Untrusted student submissions execute in a resource-bounded, non-root sandbox with strict CPU, memory, and timeout controls.
4. **Interactive Coding Workspace**: Monaco Editor with real-time feedback, sample vs hidden test runs, and clear conceptual explanations.
5. **Multi-Tenant SaaS**: Support for individual learners, educational institutions, classrooms, assignments, and quota enforcement.

---

## Monorepo Architecture

- **`apps/api`**: FastAPI backend service, SQLAlchemy 2.x ORM, Alembic migrations, Celery worker orchestration.
- **`apps/web`**: React 18, Vite, Tailwind CSS, Monaco Editor, TanStack Query.
- **`apps/execution-runner`**: Hardened execution runner protocol and worker.
- **`packages/evaluation-specifications`**: Strict Pydantic schemas for intent, AST rules, and grading rubrics.
- **`packages/api-contracts`**: Shared API models and error specifications.
- **`infrastructure/`**: Dockerfiles, Docker Compose environments, and reverse proxy configs.

---

## Getting Started

### Prerequisites
- Python 3.12+
- Node.js 20+ & npm 10+
- Docker & Docker Compose (optional for local Redis/Postgres)

### Quick Setup

```powershell
# 1. Setup Backend
python -m venv .venv
.venv\Scripts\activate
pip install -r apps/api/requirements.txt

# 2. Run Database Migrations
alembic upgrade head

# 3. Start Backend
uvicorn app.main:app --reload --port 8000

# 4. Start Frontend
cd apps/web
npm install
npm run dev
```
