# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

[1.3.0]: https://github.com/Pr0mp7/iris-data-explorer/compare/v1.2.0...v1.3.0
[1.2.0]: https://github.com/Pr0mp7/iris-data-explorer/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/Pr0mp7/iris-data-explorer/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/Pr0mp7/iris-data-explorer/releases/tag/v1.0.0
