# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Django REST API backend for an AI-powered resume and cover letter builder. Generates tailored documents from applicant profiles and job descriptions using OpenAI (gpt-4o-mini). Has a separate frontend repo ([resume_builder_v2_frontend](https://github.com/atticus-ezis/resume_builder_v2_frontend)).

## Commands

### Run locally (without Docker)
```bash
uv sync
source .venv/bin/activate
python manage.py migrate
python manage.py runserver
# Separate terminal for async AI tasks:
celery -A resume_builder worker -l info --concurrency 1
```

### Run with Docker
```bash
docker compose -f docker-compose.dev.yml up
```

### Tests
```bash
pytest                          # run all tests
pytest accounts/tests/          # run tests for one app
pytest -k test_name             # run a single test by name
```
pytest.ini configures `--reuse-db --nomigrations -v -s` by default.

### Linting
```bash
ruff check . --fix   # lint
ruff format .        # format
```
Pre-commit hooks run ruff check + format automatically.

## Architecture

### Django Apps
- **accounts** — Auth via dj-rest-auth + allauth. JWT in httpOnly cookies with rotation/blacklist. Google OAuth. No custom User model (uses `django.contrib.auth.models.User`).
- **applicant_profile** — `UserContext` model storing user resume data as JSON with SHA256 `context_hash` for dedup.
- **job_profile** — `JobDescription` model storing job posting data as JSON.
- **ai_generation** — Core generation logic. `Document` (one per user+context+job+type combo) → `DocumentVersion` (versioned outputs with auto-incrementing names and content-hash dedup).
- **resume_builder** — Django project config, Celery setup (`resume_builder/celery.py`), shared utilities (`resume_builder/utils.py`).

### Request Flow for AI Generation
1. `GenerateResumeAndCoverLetterView` receives request, dispatches Celery task
2. Celery task (`ai_generation/tasks.py`) checks for existing Document/Version (dedup via `context_hash`), calls OpenAI if needed
3. `APICall` service class builds prompts from UserContext + JobDescription, returns markdown
4. `DocumentVersion` saved with auto-generated `version_name` and `context_hash`
5. Frontend polls `TaskResultView` for async result (uses `django-celery-results` DB backend)

### Key Patterns
- **Deduplication**: Both `UserContext` and `DocumentVersion` use SHA256 content hashing with unique constraints to avoid storing duplicates
- **Celery tasks** return serialized data (not model instances) since results go through django-celery-results DB backend
- **PDF export**: `DownloadMarkdown` service converts markdown → HTML (python-markdown) → PDF (WeasyPrint) using `templates/markdown_styling.html`
- **Settings**: `django-environ` loads from `.env` file; falls back to SQLite when no `DATABASE_URL` set; Docker uses PostgreSQL

### API Structure
All API endpoints under `/api/`. Router-registered viewsets: `applicant`, `job`, `document`, `document-version`. Auth endpoints under `/api/accounts/`. OpenAPI docs at `/api/docs/`.

### Testing
Tests use `pytest-django` with `factory-boy` factories. Root `conftest.py` provides `authenticated_client` and `unauthenticated_client` fixtures. Each app has its own `tests/` directory with factories and conftest.

### Frontend
The frontend repo is at `/Users/atticusezis/coding/resume_builder_v2_frontend/`. Start with `npm run dev`.

### CI/CD
GitHub Actions (`.github/workflows/docker-publish.yml`): on push to `main`, builds Docker image → pushes to GHCR → SSH deploys to IONOS VM.
