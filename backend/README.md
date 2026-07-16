# Backend Guide

FastAPI backend for project management, simulation orchestration, result aggregation, and report generation.

## Core Stack

- FastAPI application entry: [backend/app/main.py](backend/app/main.py)
- Routers: [backend/app/routers](backend/app/routers)
- Celery tasks: [backend/app/tasks.py](backend/app/tasks.py)
- Simulation workers: [simulation](simulation)

## Runtime Modes

### Local script mode

Run all backend-side processes with [start_services.sh](start_services.sh):

- FastAPI API on port 8001
- Celery worker
- Ray simulation worker

### Hugging Face / container mode

Container startup script [start_hf_services.sh](start_hf_services.sh) launches:

- Uvicorn API server
- Celery worker
- simulation_worker.py

## API Routers

### Authentication

Defined in [backend/app/routers/auth.py](backend/app/routers/auth.py):

- POST /auth/register
- POST /auth/login
- GET /auth/me

### Projects

Defined in [backend/app/routers/projects.py](backend/app/routers/projects.py):

- POST /projects
- GET /projects
- GET /projects/{project_id}
- PATCH /projects/{project_id}/context
- DELETE /projects/{project_id}

Notes:

- Project create accepts `media_subtype` plus either a `media` file (or legacy `video`) or pasted `text_content` for email/blog subtypes.
- Supported subtypes: `video_ad`, `print_ad`, `display_banner`, `ooh`, `radio_ad`, `streaming_audio_ad`, `email_marketing`, `blog_article`.
- Files are uploaded to Hugging Face storage through the hf_storage service (modality prefixes: videos/, images/, audio/, text/).
- Celery `process_media_task` decomposes media via Gemini (or extracts/passthrough for text) into `vlm_generated_context`.

### Existing database migration

On API startup the app attempts additive PostgreSQL alters. If you manage schema manually:

```sql
ALTER TABLE projects ADD COLUMN IF NOT EXISTS media_subtype VARCHAR(50) DEFAULT 'video_ad';
ALTER TABLE projects ADD COLUMN IF NOT EXISTS media_modality VARCHAR(20) DEFAULT 'video';
ALTER TABLE projects ALTER COLUMN video_path DROP NOT NULL;
UPDATE projects SET media_subtype = 'video_ad' WHERE media_subtype IS NULL;
UPDATE projects SET media_modality = 'video' WHERE media_modality IS NULL;
```

Also install text-extraction deps if needed: `pypdf`, `python-docx` (listed in requirements.txt).

### Simulations

Defined in [backend/app/routers/simulations.py](backend/app/routers/simulations.py):

- POST /simulations/{project_id}/start
- POST /simulations/{simulation_id}/cancel
- GET /simulations/{simulation_id}
- GET /simulations/{simulation_id}/status
- GET /simulations/{simulation_id}/results
- GET /simulations/project/{project_id}
- GET /simulations/{simulation_id}/map-data
- GET /simulations/{simulation_id}/agents/{agent_id}
- GET /simulations/{simulation_id}/report

### Custom Agents

Defined in [backend/app/routers/agents.py](backend/app/routers/agents.py):

- POST /agents
- GET /agents
- GET /agents/{agent_id}
- PUT /agents/{agent_id}
- DELETE /agents/{agent_id}

## Health Endpoints

Defined in [backend/app/main.py](backend/app/main.py):

- GET /
- GET /health

/health checks:

- database connectivity
- redis connectivity

## Worker Internals Overview

### Celery path

- API starts async job via Celery task dispatch.
- Worker consumes task queue and executes simulation pipeline.

### Simulation worker path

- [simulation/simulation_worker.py](simulation/simulation_worker.py) handles simulation processing and data production.
- Results listener in [backend/app/results_listener.py](backend/app/results_listener.py) receives and stores output.

### Status flow

- Running simulation status can be cached in Redis.
- Polling endpoints read and return progress metadata.

## Configuration

Primary settings live in [backend/app/config.py](backend/app/config.py).

Important variables:

- DATABASE_URL
- REDIS_URL
- CHROMA_HOST / CHROMA_PORT / CHROMA_SSL
- GEMINI_API_KEY / GEMINI_API_KEYS
- OLLAMA_API_URL / OLLAMA_MODEL_NAME / OLLAMA_API_KEY
- HF_ACCESS_TOKEN and video repository settings
- JWT_SECRET / JWT_ALGORITHM / JWT_EXPIRY_HOURS

## Local Development

Install dependencies:

```bash
pip install -r requirements.txt
```

Run API only:

```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
```

Run full local backend process set:

```bash
./start_services.sh
```

## Troubleshooting

### 401 loops or login issues

Check token handling and Authorization header flow from frontend.

### Simulation stuck in PENDING/RUNNING

Check:

- Redis availability
- Celery worker logs
- simulation worker process logs

### Storage upload failures

Check Hugging Face token and repository configuration in environment variables.
