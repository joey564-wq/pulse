HEAD
# Pulse

A tiny service health monitor. Pings a list of URLs on demand, reports status and latency.

This is week 1 of a 4-week build. By the end it'll be a scheduled async checker
with a REST API, web dashboard, persistence, and alerting, deployed to Fly.io.

## Setup

You need [uv](https://docs.astral.sh/uv/) installed.

```bash
git clone git@github.com:YOUR_USERNAME/pulse.git
cd pulse
uv sync
```

## Usage

Edit `services.toml` to list the URLs you want to watch:

```toml
[[services]]
name = "my-site"
url = "https://my-site.com"
```

Then:

```bash
uv run pulse run
```

Output:
## Development

```bash
uv run pytest              # run tests
uv run ruff check .        # lint
uv run ruff format .       # format
```

## Roadmap

- [x] Week 1: sync CLI checker, config file, tests
- [ ] Week 2: async scheduler, SQLite persistence, structlog
- [ ] Week 3: FastAPI service, web dashboard
- [ ] Week 4: Docker, GitHub Actions CI, deploy to Fly.io, Discord alerts
=======
# Pulse

A tiny service health monitor. Pings a list of URLs on demand, reports status and latency.

This is week 1 of a 4-week build. By the end it'll be a scheduled async checker
with a REST API, web dashboard, persistence, and alerting, deployed to Fly.io.

## Setup

You need [uv](https://docs.astral.sh/uv/) installed.

```bash
git clone git@github.com:YOUR_USERNAME/pulse.git
cd pulse
uv sync
```

## Usage

Edit `services.toml` to list the URLs you want to watch:

```toml
[[services]]
name = "my-site"
url = "https://my-site.com"
```

Then:

```bash
uv run pulse run
```

Output:
## Development

```bash
uv run pytest              # run tests
uv run ruff check .        # lint
uv run ruff format .       # format
```

## Roadmap

- [x] Week 1: sync CLI checker, config file, tests
- [ ] Week 2: async scheduler, SQLite persistence, structlog
- [ ] Week 3: FastAPI service, web dashboard
- [ ] Week 4: Docker, GitHub Actions CI, deploy to Fly.io, Discord alerts
457c064 (Port checker tests to CheckResult; add db integration test)

## API

Pulse exposes a REST API and a small dashboard.

```bash
pulse serve              # starts the server at http://127.0.0.1:8000
pulse serve --reload     # with auto-reload (dev)
```

Endpoints:

| Method | Path                       | Description                            |
| ------ | -------------------------- | -------------------------------------- |
| GET    | `/health`                  | Liveness check                         |
| GET    | `/services`                | List all known service URLs            |
| GET    | `/history?url=...`         | Recent check records for a URL         |
| GET    | `/summary`                 | Aggregate stats for all services       |
| GET    | `/summary/{url:path}`      | Aggregate stats for one service        |
| GET    | `/`                        | HTML dashboard                         |

The OpenAPI docs are auto-generated at `/docs`.

## Configuration

`services.toml` controls what gets monitored:

```toml
[[services]]
url = "https://example.com"
name = "example"
interval_seconds = 30
timeout_seconds = 5
alert_after_failures = 3
```

## Alerting

When a service fails `alert_after_failures` times in a row, Pulse logs an alert and appends a JSON line to `alerts.log`. A "recovered" event fires when it succeeds again.