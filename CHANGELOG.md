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