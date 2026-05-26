# company-risk-assessment

An automated company background check service that searches multiple public data sources and uses an LLM to synthesise findings into a structured risk report.

---

## Running locally

### Prerequisites

- Python (tested with 3.11 and 3.12)
- Node.js (tested with v25.9)

### Backend

```bash
# Install dependencies
pip install -r requirements.txt

# Create a .env file with your credentials
cp .env.example .env  # or create .env manually — see Environment Variables below

# Start the API server
uvicorn app.src.main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`. Interactive docs at `http://localhost:8000/docs`.

### Frontend (UI)

```bash
cd ui
npm install
npm run dev
```

The UI will be available at `http://localhost:5173`. It proxies `/api` requests to `http://localhost:8000` automatically via the Vite dev server config.

---

## Running tests

```bash
# From the project root
pytest
```

To run a specific test file:

```bash
pytest app/tests/services/test_assessment_service.py
```

---

## Deployment (Docker Compose)

```bash
# Build and start all services
docker compose up --build -d

# View logs
docker compose logs -f
```

The backend runs on port `8000` and the UI on port `5173`.

> **Note:** The UI container uses `BACKEND_URL` (set in `docker-compose.yml`) to configure the nginx reverse proxy for API requests. Update this value to match your deployed backend URL before building.

---

## Environment variables

Create a `.env` file in the project root:

| Variable | Required | Description |
|---|---|---|
| `OPENROUTER_API_KEY` | Yes | API key for OpenRouter (used for LLM and web search) |
| `OPENROUTER_MODEL` | No | Model to use (default: `deepseek/deepseek-v4-flash`) |
| `OPENROUTER_BASE_URL` | No | OpenRouter base URL (default: `https://openrouter.ai/api/v1`) |
| `COMPANIES_HOUSE_API_KEY` | Yes | UK Companies House API key (enables the Companies House module) |
| `API_KEYS` | No | Comma-separated list of valid API keys for backend auth; leave blank to disable |
| `JOB_TTL_HOURS` | No | How long completed jobs are retained in memory (default: `24`) |
| `MODULE_TIMEOUT_SECONDS` | No | Per-module fetch timeout (default: `90`) |
