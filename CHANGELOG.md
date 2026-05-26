# Changelog

All notable changes to Pulse are documented here. The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] — 2026-05-XX

First production-quality release. Per-service task isolation, graceful shutdown, alert state persistence, retention controls, and a polished dashboard. The system is now hard to crash and demoable in one command.

### Added
- `pulse demo` — seeds 24 hours of reproducible synthetic data (seed = 42) and starts the dashboard in one command.
- `pulse stats` — one-page summary of monitoring history: services tracked, total checks, uptime %, alert counts, currently-active alerts.
- `pulse prune` — retention via `--days N` (by age) or `--keep-last N` (per-service record count).
- Alert state persistence — `AlertTracker` failure counters and active-alert state survive `pulse monitor` restarts via new `alert_state` and `alert_event` tables.
- `alerts_persistence` module — bridges the pure `AlertTracker` state machine to the database without coupling them.
- `TrackerState` dataclass plus `state_for()` and `hydrate()` methods on `AlertTracker` for restart-safe persistence.
- `/stats` and `/alerts/recent` REST endpoints, with corresponding `OverallStatsOut` and `AlertEventOut` response models.
- `get_overall_stats()` and `get_recent_alerts()` query functions in `queries.py`.
- Dashboard CSS pass — design-token palette (HSL), system font stack, six-step type scale, sparklines per service, recent-alerts panel, stat bar, dark mode via `prefers-color-scheme`, mobile-responsive layout.
- README rewrite with architecture diagram (mermaid), "Run in 30 seconds" quick start, CLI/API reference tables, and out-of-scope statement.

### Changed
- **Per-service task isolation in `monitor.py`** — one failing service no longer cancels the others. Inner `try/except` guards each service loop; `asyncio.gather(..., return_exceptions=True)` is a backstop.
- **Graceful Ctrl-C shutdown** — `pulse monitor` now exits cleanly via an `asyncio.Event`-driven stop signal and cooperative `asyncio.wait_for` sleeps. Closes the HTTP client and disposes the engine without a traceback.
- **`ConfigError`** raised for malformed `services.toml` — single-line, human-readable error replacing the previous Pydantic traceback. CLI catches it and exits with code 2.
- **`api.py` reads `PULSE_DB` env var** in its lifespan instead of hardcoding `pulse.db` at module load time. Enables `pulse serve --db ...` and `pulse demo` to override the database path.
- FastAPI `version` metadata bumped to `1.0.0`; `pyproject.toml` version bumped to `1.0.0`; `description` filled in; `[project.urls]` section added.

## [0.3.0] — 2026-05-XX

### Added
- FastAPI REST API with endpoints for services, history, and summaries.
- Single-page HTML dashboard with auto-refresh, served at `/`.
- `pulse serve` CLI command.
- Per-service configuration: `name`, `interval_seconds`, `timeout_seconds`, `alert_after_failures`.
- Alerting on consecutive failures via `LogNotifier` and `FileNotifier`.
- Pydantic response models for clean API serialization (`CheckRecordOut`, `ServiceSummaryOut`).
- `queries.py` shared by the CLI and the API.

### Changed
- `run_monitor` signature: now takes `list[Service]` instead of `list[str]` and global `interval_seconds`. Per-service intervals run as concurrent tasks via `asyncio.gather`.
- `Service` model gains four new fields with sensible defaults; existing TOML files load unchanged.
- `monitor` CLI command no longer accepts `--interval`; intervals come from `services.toml`.

[1.0.0]: https://github.com/joey564-wq/pulse/releases/tag/v1.0.0
[0.3.0]: https://github.com/joey564-wq/pulse/releases/tag/v0.3.0