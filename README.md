# AI Voice Studio

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

## Run With Docker

```powershell
cd C:\SLABS\docker
docker compose up --build
```
