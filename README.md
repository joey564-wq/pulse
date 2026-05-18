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
