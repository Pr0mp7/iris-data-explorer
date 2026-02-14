# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.5.0] - 2026-02-14

### Added
- Entity count badges on tabs — shows record count (e.g. `Assets (12)`) for instant triage awareness
- Keyboard shortcuts — `Alt+1`–`Alt+7` switch tabs, `Alt+←/→` cycle, `Esc` close modals
- Click row to expand full record — inline detail panel showing all fields untruncated
- Resolve IDs to human labels — asset types, IOC types, TLP, status, severity display readable names via IRIS lookup endpoints
- Persistent table state — page, sort, and filters preserved across tab switches and page refreshes
- Status, Severity, and Owner columns on cases list — previously hidden API fields now displayed
- Previous/Next case navigation buttons in case header
- Manual "Refresh Now" button next to auto-refresh timer
- TLP color-coded badges — RED/AMBER/GREEN/CLEAR with standard colors
- IOC context menu — right-click IOC rows for VirusTotal, AbuseIPDB, Shodan, Censys lookups
- Page length selector — choose 10/25/50/100 rows per page on all DataTables
- Breadcrumb navigation (`All Cases > Case #42`) below case header
- Sticky table headers — column headers stay visible when scrolling long tables
- Deep links to specific IRIS entities — ID links open exact entity page, not the list
- Status/Severity badges in case explorer header — color-coded Open/Closed + severity indicators
- Shadowserver indicator count feedback — "Searched 5 IPs, 2 hostnames — 0 matches"
- Copy row as JSON — full row data available via expand panel
- Deferred tab loading — only active tab loads initially; others init on first click (7→1 initial API calls)
- `/api/lookups` endpoint — serves IRIS lookup tables for client-side label resolution
- `/api/case-neighbors/<id>` endpoint — returns previous/next case IDs for navigation

## [1.4.2] - 2026-02-13

### Security
- Server-side sessions via `flask-session` — API key never stored in client cookie
- Session cookie flags: `HttpOnly`, `SameSite=Lax`, configurable `Secure`
- CSRF protection on logout (POST with token)
- HSTS header (`Strict-Transport-Security: max-age=31536000`)
- Full Content-Security-Policy (`script-src`, `style-src`, `font-src`, `img-src`, `connect-src`)
- Configurable `DB_SSL_MODE` / `SS_DB_SSL_MODE` for PostgreSQL connections
- File-based rate limiter storage (works across gunicorn workers)
- Startup warning when `SECRET_KEY` is auto-generated
- Default rate limit (120/min) on all API endpoints
- Cache invalidation on user logout
- Open redirect fix: backslash normalization + `urlparse` validation
- Sanitized error logging (`log.error` instead of `log.exception`)
- Removed redundant `X-Frame-Options` (CSP `frame-ancestors` sufficient)
- Docker read-only root filesystem with `tmpfs` for `/tmp`
- Docker base image pinned by SHA256 digest

### Changed
- `psycopg2-binary` replaced with `psycopg2` (uses system `libpq`)

### Dependencies
- Added `flask-session==0.8.0` (server-side sessions)

### Fixed
- Rate limiter reverted to `memory://` (`file://` not supported)
- psycopg2 build: added `libc6-dev` for C headers
- Removed unused logo files

## [1.4.1] - 2026-02-13

### Fixed
- Suppress noisy `urllib3 InsecureRequestWarning` logs when `IRIS_VERIFY_SSL=false`

## [1.4.0] - 2026-02-13

### Changed
- Complete CSS rewrite matching the official DFIR-IRIS dark navy design language
- Dark theme: `#121622` body, `#1f283e` navbar, `#202940` cards — identical to IRIS
- Light theme: `#f9fbfd` body with `#05316a` navy navbar
- Official IRIS logos (white + blue variants) and favicon
- Lato font via Google Fonts
- IRIS-style login page with radial gradient background
- Theme-aware pagination, tabs, cards, inputs, buttons, modals

### Fixed
- Column filters added to Shadowserver browse page
- DataTable pagination buttons styled with IRIS tokens
- Light theme login page fully styled
- Focus-visible states for keyboard accessibility
- Dark modal close button visibility fixed
- Error page uses IRIS accent styling
- Cases page header wrapped in styled card
- Footer added to all pages
- `aria-label` on theme toggle

### Other
- Explicit `image:` tag in docker-compose (fixes doubled image name)
- Python 3.13 upgrade
- Static license badge (avoids shields.io rate limits)

## [1.3.2] - 2026-02-13

### Security
- CSRF token on login form — prevents forged login requests
- Rate limiting on login endpoint (10/min per IP) via Flask-Limiter
- Session timeout after 8 hours (configurable via `SESSION_TIMEOUT_HOURS`)

### Changed
- PostgreSQL connection pooling for both IRIS DB and Shadowserver DB (replaces per-request connections)
- Bounded LRU cache (max 256 entries) with automatic eviction — prevents unbounded memory growth
- Pagination safety limit (10,000 items max) on IRIS API fetcher — prevents OOM on huge cases
- Docker resource limits (1 CPU, 512MB RAM) and log rotation (10MB x 3 files) on both compose files

## [1.3.1] - 2026-02-13

### Security
- Fixed open redirect vulnerability on login `next` parameter — now validates relative paths only
- Added security headers: `X-Frame-Options`, `Referrer-Policy`, `Permissions-Policy`
- Sanitized error messages — no longer leaks internal hostnames, ports, or stack traces to users
- Fixed raw data expand button on global Shadowserver page (base64 encoding, matching case explorer fix)
- Container now runs as non-root user (`appuser`)

### Added
- Access logging — logs case views, auth attempts (success/failure), and API errors
- Input validation on DataTables `start`/`length` parameters (clamped to sane bounds)

## [1.3.0] - 2026-02-13

### Changed
- Removed `shadowserver-ingestor/` — now a separate repo at [Pr0mp7/shadowserver-ingestor](https://github.com/Pr0mp7/shadowserver-ingestor)

## [1.2.0] - 2026-02-13

### Added
- Per-column filter inputs on all DataTables (Assets, IOCs, Timeline, Tasks, Notes, Evidence, Shadowserver, cases list)
- Debounced filter inputs (300ms) with SQL ILIKE support for Shadowserver columns
- Column filters work alongside existing global search

## [1.1.0] - 2026-02-13

### Added
- Shadowserver integration — UI for browsing and correlating Shadowserver scan data
- Global Shadowserver data browser (`/shadowserver`) with filter bar, summary cards, and ingestion log
- Dynamic Shadowserver tab inside case explorer — correlates case IOCs/Assets (IPs, hostnames, ASNs) with Shadowserver events
- Expandable raw event data modal in Shadowserver views

### Fixed
- Raw data expand button encoding (base64 for safe HTML attribute storage)

## [1.0.0] - 2026-02-13

### Added
- Initial release
- Interactive case explorer with 6 entity tabs (Assets, IOCs, Timeline, Tasks, Notes, Evidence)
- Server-side DataTables with sorting, filtering, search, and pagination
- Cases list page with search
- Pass-through authentication (users log in with their own IRIS API key)
- Service mode authentication (shared API key, no login)
- CSV and clipboard export on all tables
- Auto-refresh with configurable interval
- Dark/Light theme toggle
- Deep links to IRIS case entities
- Copy-to-clipboard buttons on IPs, hashes, IOC values
- Air-gapped — all JS/CSS bundled locally
- Two data modes: IRIS REST API or direct PostgreSQL
- Docker deployment with healthcheck
- Lab deployment with external Docker network support

[1.5.0]: https://github.com/Pr0mp7/iris-data-explorer/compare/v1.4.2...v1.5.0
[1.4.2]: https://github.com/Pr0mp7/iris-data-explorer/compare/v1.4.1...v1.4.2
[1.4.1]: https://github.com/Pr0mp7/iris-data-explorer/compare/v1.4.0...v1.4.1
[1.4.0]: https://github.com/Pr0mp7/iris-data-explorer/compare/v1.3.2...v1.4.0
[1.3.2]: https://github.com/Pr0mp7/iris-data-explorer/compare/v1.3.1...v1.3.2
[1.3.1]: https://github.com/Pr0mp7/iris-data-explorer/compare/v1.3.0...v1.3.1
[1.3.0]: https://github.com/Pr0mp7/iris-data-explorer/compare/v1.2.0...v1.3.0
[1.2.0]: https://github.com/Pr0mp7/iris-data-explorer/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/Pr0mp7/iris-data-explorer/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/Pr0mp7/iris-data-explorer/releases/tag/v1.0.0
