# AI Voice Studio Backend

FastAPI backend scaffold for AI Voice Studio.

## Run Locally

```powershell
cd C:\SLABS\backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Health check:

```text
GET http://127.0.0.1:8000/api/v1/health
```

## MVP Endpoints

```text
POST   /api/v1/voices/register
GET    /api/v1/voices
GET    /api/v1/voices/{voice_id}
DELETE /api/v1/voices/{voice_id}

POST   /api/v1/tts/generate
GET    /api/v1/tts/jobs/{job_id}
GET    /api/v1/tts/download/{job_id}

POST   /api/v1/audio/clean
POST   /api/v1/audio/enhance
POST   /api/v1/audio/normalize

POST   /api/v1/projects
GET    /api/v1/projects
GET    /api/v1/projects/{project_id}
```

The current voice engines are adapter placeholders for `dummy`, `xtts`, `f5tts`, and `fishspeech`.
They preserve the pluggable architecture while real model integrations are added.

## Source Layout

```text
app/
  api_routes/
  application_core/
  audio_enhancement/
  audio_export/
  audio_mixing/
  background_workers/
  business_services/
  content_preprocessing/
  domain_models/
  emotion_analysis/
  pronunciation_dictionary/
  request_schemas/
  shared_utils/
  voice_engines/
```

## Run With Docker

```powershell
cd C:\SLABS\docker
docker compose up --build
```
