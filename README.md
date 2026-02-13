<p align="center">
  <h1 align="center">IRIS Data Explorer</h1>
  <p align="center">
    Interactive case data explorer for <a href="https://github.com/dfir-iris/iris-web">DFIR-IRIS</a><br>
    Sortable, filterable, exportable DataTables for all case entities — with optional Shadowserver correlation.
  </p>
</p>

<p align="center">
  <a href="https://github.com/Pr0mp7/iris-data-explorer/releases"><img src="https://img.shields.io/github/v/release/Pr0mp7/iris-data-explorer?style=flat-square&color=blue" alt="Release"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-LGPL--3.0-blue?style=flat-square" alt="License"></a>
  <img src="https://img.shields.io/badge/python-3.13-blue?style=flat-square&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/docker-ready-blue?style=flat-square&logo=docker&logoColor=white" alt="Docker">
</p>

---

## Features

- **7 entity tabs** — Assets, IOCs, Timeline, Tasks, Notes, Evidence, Shadowserver
- **Per-column filters** — filter inputs below every column header
- **Server-side DataTables** — sorting, search, pagination, CSV/clipboard export
- **Shadowserver correlation** — matches case IOCs/Assets against Shadowserver scan data *(optional)*
- **Dark/Light theme** — toggle with localStorage persistence
- **Pass-through auth** — users log in with their own IRIS API key
- **Air-gapped** — all JS/CSS bundled locally, zero CDN calls
- **Deep links** — click-through to IRIS case entities
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

## Architecture

```
Browser ──► IRIS Data Explorer (Flask, port 8087)
                │
                ├──► IRIS REST API v2 (case data)
                │
                └──► PostgreSQL: shadowserver_db (read-only, optional)
                          ▲
                          │ writes (separate service)
                    shadowserver-ingestor
                          │
                          ▼
                    Shadowserver API
```

The explorer is **read-only** — it never modifies case data.

## Configuration

<details>
<summary><strong>Required</strong></summary>

| Variable | Default | Description |
|----------|---------|-------------|
| `IRIS_URL` | `https://localhost:4443` | IRIS instance URL (internal/Docker) |
| `IRIS_EXTERNAL_URL` | *same as IRIS_URL* | Browser-facing IRIS URL for deep links |
| `IRIS_VERIFY_SSL` | `false` | Verify TLS certificate |

</details>

<details>
<summary><strong>Authentication</strong></summary>

| Variable | Default | Description |
|----------|---------|-------------|
| `IRIS_API_KEY` | *(empty)* | If set, all users share this key (service mode). If empty, users log in with their own IRIS API key (pass-through mode) |
| `SECRET_KEY` | *auto-generated* | Flask session encryption key. Set for persistent sessions across restarts |

</details>

<details>
<summary><strong>General</strong></summary>

| Variable | Default | Description |
|----------|---------|-------------|
| `DATA_SOURCE` | `api` | `api` (IRIS REST API) or `db` (direct PostgreSQL) |
| `EXPLORER_PORT` | `8087` | Host port mapping |
| `CACHE_TTL` | `300` | Data cache duration in seconds |
| `REFRESH_INTERVAL` | `30` | Auto-refresh interval in seconds (0 = disabled) |

</details>

<details>
<summary><strong>Database Mode</strong> (optional — direct PostgreSQL instead of IRIS API)</summary>

| Variable | Default | Description |
|----------|---------|-------------|
| `DB_HOST` | `localhost` | PostgreSQL host |
| `DB_PORT` | `5432` | PostgreSQL port |
| `DB_NAME` | `iris_db` | Database name |
| `DB_USER` | `iris` | Database user (read-only recommended) |
| `DB_PASSWORD` | *(required)* | Database password |

</details>

<details>
<summary><strong>Shadowserver Integration</strong> (optional)</summary>

Correlates case IOCs and Assets with [Shadowserver](https://www.shadowserver.org/) scan data. Requires the [shadowserver-ingestor](https://github.com/Pr0mp7/shadowserver-ingestor) service.

| Variable | Default | Description |
|----------|---------|-------------|
| `SS_ENABLED` | `false` | Enable Shadowserver tab and global browse page |
| `SS_DB_HOST` | `postgres` | Shadowserver database host |
| `SS_DB_PORT` | `5432` | Shadowserver database port |
| `SS_DB_NAME` | `shadowserver_db` | Shadowserver database name |
| `SS_DB_USER` | `shadowserver_viewer` | Read-only database user |
| `SS_DB_PASSWORD` | *(required)* | Database password |

</details>

## Endpoints

| Route | Description |
|-------|-------------|
| `GET /` | Cases list with search and pagination |
| `GET /case/<id>` | Interactive explorer with all entity tabs |
| `GET /shadowserver` | Global Shadowserver data browser (when `SS_ENABLED=true`) |
| `GET /health` | Health check |

<details>
<summary><strong>API Endpoints</strong></summary>

| Route | Description |
|-------|-------------|
| `GET /api/dt/cases` | DataTables server-side — cases list |
| `GET /api/dt/case/<id>/<entity>` | DataTables server-side — case entities |
| `GET /api/dt/case/<id>/shadowserver` | DataTables server-side — Shadowserver correlation |
| `GET /api/dt/shadowserver` | DataTables server-side — global Shadowserver browse |
| `GET /api/shadowserver/stats` | Shadowserver summary statistics |
| `GET /api/shadowserver/report-types` | Available Shadowserver report types |

</details>

## Deployment

**Standalone:**

```bash
docker compose up -d
```

**Lab** (with IRIS on Docker network):

```bash
docker compose -f docker-compose.lab.yml up -d
```

Connects to `iris_frontend` and `postgres-net` external Docker networks.

## Related

- **[shadowserver-ingestor](https://github.com/Pr0mp7/shadowserver-ingestor)** — fetches Shadowserver scan reports into PostgreSQL (required for Shadowserver features)
- **[DFIR-IRIS](https://github.com/dfir-iris/iris-web)** — the incident response platform this tool extends

## License

[LGPL-3.0](LICENSE)
