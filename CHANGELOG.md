# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2026-02-13

### Added
- Shadowserver integration with standalone ingestor service
- Global Shadowserver data browser (`/shadowserver`) with filter bar, summary cards, and ingestion log
- Dynamic Shadowserver tab inside case explorer — correlates case IOCs/Assets (IPs, hostnames, ASNs) with Shadowserver events
- Expandable raw event data modal in Shadowserver views
- Shadowserver ingestor: HMAC-SHA256 API client, CSV report download, SHA256 dedup, APScheduler, health endpoint
- PostgreSQL schema with hybrid indexed columns + JSONB for flexible event storage

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

[1.1.0]: https://github.com/Pr0mp7/iris-data-explorer/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/Pr0mp7/iris-data-explorer/releases/tag/v1.0.0
