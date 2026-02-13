# IRIS Data Explorer

Interactive case data explorer for [DFIR-IRIS](https://github.com/dfir-iris/iris-web) — a standalone Docker service that provides sortable, filterable, and exportable DataTables for all case entities.

## Features

- **7 entity tabs**: Assets, IOCs, Timeline, Tasks, Notes, Evidence
- **Sortable & filterable** DataTables with search
- **CSV export** on every table
- **Dark/Light theme** toggle
- **Air-gapped** — all JS/CSS bundled, zero CDN calls
- **Two data modes**: IRIS REST API (default) or direct PostgreSQL
- **Zero IRIS modification** — works with any IRIS version that has v2 API

## Quick Start

```bash
git clone https://github.com/Pr0mp7/iris-data-explorer.git
cd iris-data-explorer
cp .env.example .env
# Edit .env with your IRIS URL and API key
docker compose up -d
```

Open `http://localhost:8087` in your browser.

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `IRIS_URL` | `https://localhost:4443` | IRIS instance URL |
| `IRIS_API_KEY` | *(required)* | IRIS API key (Bearer token) |
| `IRIS_VERIFY_SSL` | `false` | Verify TLS certificate |
| `DATA_SOURCE` | `api` | `api` or `db` |
| `EXPLORER_PORT` | `8087` | Host port mapping |
| `AUTH_CACHE_TTL` | `300` | API key cache duration (seconds) |

### Database Mode (optional)

Set `DATA_SOURCE=db` and configure:

| Variable | Default | Description |
|----------|---------|-------------|
| `DB_HOST` | `localhost` | PostgreSQL host |
| `DB_PORT` | `5432` | PostgreSQL port |
| `DB_NAME` | `iris_db` | Database name |
| `DB_USER` | `iris` | Database user |
| `DB_PASSWORD` | *(required)* | Database password |

## Endpoints

| Route | Description |
|-------|-------------|
| `GET /` | Cases list |
| `GET /case/<id>` | Interactive explorer for a case |
| `GET /api/case/<id>` | JSON API — all case entities |
| `GET /health` | Health check |

## Getting Your API Key

1. Log into IRIS
2. Go to **User Profile** > **My Settings**
3. Copy your **API Key**

## Architecture

```
Browser → IRIS Data Explorer (Flask + DataTables)
              ↓
         IRIS REST API v2  (API mode, default)
              or
         PostgreSQL direct (DB mode, optional)
```

The explorer is a **read-only** service. It never modifies case data.

## Lab Deployment

For environments with IRIS on a Docker network:

```bash
docker compose -f docker-compose.lab.yml up -d
```

This connects to the `iris_frontend` external network so the explorer can reach IRIS by container name.

## License

LGPL-3.0 — see [LICENSE](LICENSE).
