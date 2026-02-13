# IRIS Data Explorer

Interactive case data explorer for [DFIR-IRIS](https://github.com/dfir-iris/iris-web) — a standalone Docker service that provides sortable, filterable, and exportable DataTables for all case entities.

## Features

- **7 entity tabs**: Assets, IOCs, Timeline, Tasks, Notes, Evidence
- **Shadowserver integration**: Correlates case IOCs/Assets with Shadowserver scan data (optional)
- **Server-side DataTables** with sorting, filtering, search, and pagination
- **CSV/clipboard export** on every table
- **Auto-refresh** with configurable interval
- **Dark/Light theme** toggle
- **Deep links** to IRIS case entities
- **Copy-to-clipboard** buttons on IPs, hashes, IOC values
- **Air-gapped** — all JS/CSS bundled locally, zero CDN calls
- **Two data modes**: IRIS REST API (default) or direct PostgreSQL
- **Pass-through auth** — users log in with their own IRIS API key
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

### Required

| Variable | Default | Description |
|----------|---------|-------------|
| `IRIS_URL` | `https://localhost:4443` | IRIS instance URL (internal/Docker) |
| `IRIS_EXTERNAL_URL` | *same as IRIS_URL* | Browser-facing IRIS URL for deep links |
| `IRIS_VERIFY_SSL` | `false` | Verify TLS certificate |

### Authentication

| Variable | Default | Description |
|----------|---------|-------------|
| `IRIS_API_KEY` | *(empty)* | If set, all users share this key (service mode). If empty, users log in with their own IRIS API key (pass-through mode) |
| `SECRET_KEY` | *auto-generated* | Flask session encryption key. Set for persistent sessions across restarts |

### General

| Variable | Default | Description |
|----------|---------|-------------|
| `DATA_SOURCE` | `api` | `api` (IRIS REST API) or `db` (direct PostgreSQL) |
| `EXPLORER_PORT` | `8087` | Host port mapping |
| `CACHE_TTL` | `300` | Data cache duration in seconds |
| `REFRESH_INTERVAL` | `30` | Auto-refresh interval in seconds (0 = disabled) |

### Database Mode (optional)

Set `DATA_SOURCE=db` for direct PostgreSQL access instead of the IRIS API:

| Variable | Default | Description |
|----------|---------|-------------|
| `DB_HOST` | `localhost` | PostgreSQL host |
| `DB_PORT` | `5432` | PostgreSQL port |
| `DB_NAME` | `iris_db` | Database name |
| `DB_USER` | `iris` | Database user (read-only recommended) |
| `DB_PASSWORD` | *(required)* | Database password |

### Shadowserver Integration (optional)

Correlates case IOCs and Assets with [Shadowserver](https://www.shadowserver.org/) scan data. Requires the `shadowserver-ingestor` service writing data to a PostgreSQL database.

| Variable | Default | Description |
|----------|---------|-------------|
| `SS_ENABLED` | `false` | Enable Shadowserver tab in case explorer and global browse page |
| `SS_DB_HOST` | `postgres` | Shadowserver database host |
| `SS_DB_PORT` | `5432` | Shadowserver database port |
| `SS_DB_NAME` | `shadowserver_db` | Shadowserver database name |
| `SS_DB_USER` | `shadowserver_viewer` | Read-only database user |
| `SS_DB_PASSWORD` | *(required)* | Database password |

## Endpoints

| Route | Description |
|-------|-------------|
| `GET /` | Cases list with search and pagination |
| `GET /case/<id>` | Interactive explorer with all entity tabs |
| `GET /shadowserver` | Global Shadowserver data browser (when `SS_ENABLED=true`) |
| `GET /health` | Health check |

### API Endpoints

| Route | Description |
|-------|-------------|
| `GET /api/dt/cases` | DataTables server-side — cases list |
| `GET /api/dt/case/<id>/<entity>` | DataTables server-side — case entities (assets, iocs, events, tasks, notes, evidences) |
| `GET /api/dt/case/<id>/shadowserver` | DataTables server-side — Shadowserver events correlated with case indicators |
| `GET /api/dt/shadowserver` | DataTables server-side — global Shadowserver browse |
| `GET /api/shadowserver/stats` | Shadowserver summary statistics |
| `GET /api/shadowserver/report-types` | Available Shadowserver report types |

## Architecture

```
Browser ──► IRIS Data Explorer (Flask, port 8087)
                │
                ├──► IRIS REST API v2 (case data)
                │
                └──► PostgreSQL: shadowserver_db (read-only, optional)
                          ▲
                          │ writes
                Shadowserver Ingestor (standalone container)
                          │
                          ▼
                Shadowserver API (HMAC-SHA256 auth)
```

The explorer is a **read-only** service. It never modifies case data.

## Shadowserver Ingestor

The `shadowserver-ingestor/` directory contains a standalone service that fetches scan reports from the Shadowserver API and writes them to PostgreSQL.

See [`shadowserver-ingestor/`](shadowserver-ingestor/) for setup and configuration.

**Key features:**
- HMAC-SHA256 authenticated API client
- Fetches all subscribed report types as CSV
- SHA256-based dedup (no duplicate events)
- Configurable schedule (default: every 15 minutes)
- Auto-backfill on first start (default: 7 days)
- Health endpoint on port 8088
- Ingestion audit log

## Deployment

### Standalone

```bash
docker compose up -d
```

### Lab (with IRIS on Docker network)

```bash
docker compose -f docker-compose.lab.yml up -d
```

Connects to `iris_frontend` and `postgres-net` external Docker networks.

### With Shadowserver Ingestor

```bash
# 1. Start the ingestor (writes to PostgreSQL)
cd shadowserver-ingestor
cp .env.example .env  # configure API keys + DB credentials
docker compose up -d

# 2. Start the explorer (reads from PostgreSQL)
cd ..
cp .env.example .env  # set SS_ENABLED=true + DB credentials
docker compose -f docker-compose.lab.yml up -d
```

## License

LGPL-3.0 — see [LICENSE](LICENSE).
