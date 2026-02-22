# CI/CD Pipeline Guideline

This document describes how to set up and maintain a CI/CD pipeline for the **celery-fastapi-boilerplate** project (FastAPI backend + Celery + Next.js frontend).

---

## 1. Overview

| Component   | Stack              | CI checks to run                    |
|------------|--------------------|-------------------------------------|
| **Backend**  | Python 3.12, FastAPI, Celery | Lint, tests, Docker build |
| **Frontend** | Node 24, Next.js 14         | Lint, tests, build          |
| **Infra**    | Docker, Redis                | Optional: e2e with compose  |

---

## 2. Pipeline Stages (recommended order)

1. **Lint** – Code style and static checks (fast, fail early).
2. **Test** – Unit/integration tests for backend and frontend.
3. **Build** – Build Docker images (and/or Next.js) to ensure they succeed.
4. **Deploy** (optional) – Push images / deploy to staging or production.

---

## 3. Backend (Python / FastAPI / Celery)

### 3.1 Linting & formatting

- **ruff** or **flake8** for linting.
- **black** for formatting (optional in CI if you enforce it locally).

Example (using ruff):

```bash
pip install ruff
ruff check backend/
ruff format --check backend/
```

If you use flake8 (e.g. `backend/.flake8`), run:

```bash
pip install flake8
flake8 backend/
```

### 3.2 Tests

- Use **pytest**.
- Add a `tests/` directory and run: `pytest backend/tests -v`.
- Optionally use a `conftest.py` for fixtures and a minimal test that imports the app and hits the health/task endpoint (no Redis/Celery broker in CI unless you add services).

Example minimal test:

```python
# backend/tests/test_main.py
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
```

### 3.3 Docker build

- Build the backend image to ensure `Dockerfile` and `requirements.txt` are valid:

```bash
docker build -t backend:ci ./backend
```

---

## 4. Frontend (Next.js)

### 4.1 Lint

- **ESLint** (you have `.eslintrc.json`):

```bash
cd frontend && npm ci && npm run lint
```

Add a `lint` script in `package.json` if missing:

```json
"scripts": {
  "lint": "next lint"
}
```

### 4.2 Tests

- **Jest** + **React Testing Library** for unit/component tests (add when you have tests).
- In CI: `npm run test` or `npm run test:ci` (e.g. with `--ci` for Jest).

### 4.3 Build

- Ensures the app builds and has no build-time errors:

```bash
cd frontend && npm ci && npm run build
```

### 4.4 Docker build

- Build the frontend image:

```bash
docker build -t frontend:ci ./frontend
```

---

## 5. GitHub Actions workflow (conceptual)

- **Trigger**: The current workflow runs on **push to `main`** only. You can add `pull_request: branches: [main]` to run on PRs as well.
- **Jobs** (see `.github/workflows/ci-cd.yml` for the current set):
  - **backend-lint**: install deps, run flake8 (or ruff).
  - **backend-test**: install deps, run pytest.
  - **backend-build**: build backend Docker image.
  - **frontend-lint**: `npm ci`, `npm run lint`.
  - **frontend-build**: `npm ci`, `npm run build`; **frontend-docker-build**: build frontend image. (No `frontend-test` job yet; add when tests exist.)
  - **deploy**: run only on `main` after all jobs pass; SSH + rsync + `docker compose` on the server.

---

## 6. Single-server deploy (SSH)

The workflow includes a **deploy** job that runs only on push to `main`/`master` (after all CI jobs pass). It syncs the repo to the server via **rsync** over **SSH** and runs **Docker Compose** there.

### 6.1 GitHub Actions secrets

In the repo: **Settings → Secrets and variables → Actions**, add:

| Secret           | Description | Example |
|------------------|-------------|---------|
| `SSH_HOST`       | Server IP or hostname | `194.59.214.133` |
| `SSH_USER`       | SSH login user | `user` |
| `SSH_PRIVATE_KEY`| Full private key (e.g. `id_ed25519` or `id_rsa`) for `SSH_USER@SSH_HOST` | Paste key contents |
| `DEPLOY_PATH`    | (Optional) Path on server where the app is deployed. If unset, default is `/home/<SSH_USER>/projects/hse/git/celery-fastapi-boilerplate` | e.g. `/home/user/projects/hse/git/celery-fastapi-boilerplate` |

### 6.1.1 SSH key setup (public vs private)

- **Private key** → GitHub only: paste the **entire** key (including `-----BEGIN ... KEY-----` and `-----END ... KEY-----`) into the `SSH_PRIVATE_KEY` secret. Never commit it.
- **Public key** → Server only: add the matching public key as a **single line** in `~/.ssh/authorized_keys` for `SSH_USER` on the server (`chmod 700 ~/.ssh`, `chmod 600 ~/.ssh/authorized_keys`).
- Prefer a **dedicated deploy key**: e.g. `ssh-keygen -t ed25519 -C "github-actions-deploy" -f ~/.ssh/deploy_key -N ""`; use that pair only for this repo and server.

### 6.2 One-time server setup

On the server (e.g. `ssh user@194.59.214.133`):

1. **Install Docker and Docker Compose** (v2):
   ```bash
   curl -fsSL https://get.docker.com | sh
   sudo usermod -aG docker $USER
   # Log out and back in so docker runs without sudo
   ```

2. **Create app directory** (must match `DEPLOY_PATH` or the default `/home/<user>/projects/hse/git/celery-fastapi-boilerplate`):
   ```bash
   mkdir -p ~/projects/hse/git/celery-fastapi-boilerplate
   cd ~/projects/hse/git/celery-fastapi-boilerplate
   ```

3. **Create `.env`** (not in git; create once and keep it):
   ```bash
   cp .env.example .env
   nano .env   # set APP_PORT, FRONT_PORT, FLOWER_PORT, CELERY_BROKER_URL, CELERY_RESULT_BACKEND, CORS_ORIGINS
   ```
   The deploy job does **not** overwrite `.env` (it is excluded from rsync), so your production env stays intact.

4. **Allow GitHub Actions to SSH in**: See §6.1.1. Add the **public** key that matches `SSH_PRIVATE_KEY` to `~/.ssh/authorized_keys` for `SSH_USER` on the server.

### 6.3 What the deploy job does

1. After CI passes, it runs only for pushes to `main` or `master`.
2. Uses `rsync` to copy the repo (excluding `.git`, `node_modules`, `.next`, `__pycache__`, `.env`) to `SSH_USER@SSH_HOST:DEPLOY_PATH`.
3. SSHs into the server and runs: `docker compose -f docker-compose.prod.yml up -d --build`.

### 6.4 Your connection details (for reference)

- **Host**: `abrisham_vm` → `194.59.214.133`
- **User**: `user`

Use the same values for `SSH_HOST` and `SSH_USER` in GitHub secrets (or use `abrisham_vm` for `SSH_HOST` if it resolves from the runner).

---

## 7. Secrets and environment (general)

- **Secrets**: Store in GitHub **Settings → Secrets and variables → Actions** (e.g. `SSH_PRIVATE_KEY`, `SSH_HOST`, `SSH_USER`).
- **Env vars**: Use `env` in the workflow or inject from secrets; never commit `.env` or real credentials.
- For **staging/production**, you can add a GitHub **Environment** (e.g. `production`) and require approval before deploy.

---

## 8. Docker Compose in CI (optional)

- To run e2e or integration tests with Redis/Celery:

```yaml
services:
  redis:
    image: redis:7
```

- Start services with `docker compose up -d`, run tests, then `docker compose down`.

---

## 9. Checklist

- [ ] Backend: add pytest and at least one test; run in CI.
- [ ] Backend: add ruff or flake8 and run in CI.
- [ ] Frontend: add `lint` script and run in CI.
- [ ] Frontend: add tests and `test` script when ready; run in CI.
- [ ] Both: Docker build in CI to catch Dockerfile/context issues.
- [ ] Configure branch protection so PRs require CI to pass.
- [ ] Add deploy step only when staging/production is ready; use secrets for all credentials.

---

## 10. Example: minimal workflow file

See [../.github/workflows/ci-cd.yml](../.github/workflows/ci-cd.yml) for the current workflow. It runs:

- **Backend**: lint (flake8), tests (pytest), Docker build.
- **Frontend**: lint (ESLint), build (Next.js), Docker build.
- **Deploy**: only on push to `main` after all jobs pass; rsync to server + `docker compose -f docker-compose.prod.yml up -d --build`.

Adjust branch triggers, Python/Node versions, and deploy path/secrets to match your repo and server.
