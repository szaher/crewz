# CrewAI Platform (Crewzx)

A production-ready platform for building and executing CrewAI workflows with a visual drag-and-drop interface.

## 🚀 Quick Start

**Get up and running in 5 minutes:**

```bash
# Start services
docker-compose up -d

# Create default examples
docker-compose exec backend python3 scripts/create_defaults.py

# Open the platform
open http://localhost:3001
```

**See detailed guide:** [QUICK_START.md](./QUICK_START.md)

## 📚 Documentation

- **[Quick Start Guide](./QUICK_START.md)** - Get started in 5 minutes
- **[Default Examples](./DEFAULT_EXAMPLES.md)** - Working flows, crews, and agents
- **[Implementation Guide](./DEFAULT_EXAMPLES_IMPLEMENTATION.md)** - Technical details
- **[UI Features](./README_UI_FIXES.md)** - Platform capabilities
- **[Testing Guide](./TESTING_GUIDE.md)** - Manual testing procedures

## ✨ Features

- ✅ Visual flow builder with drag-and-drop
- ✅ Pre-configured agents (Research Analyst, Content Writer, Travel Expert)
- ✅ Default tools (Web Search, File Reader, Calculator)
- ✅ Real-time execution monitoring
- ✅ Metrics dashboard with auto-refresh
- ✅ Multi-tenant architecture
- ✅ Production-ready with Docker Compose

## 🏗️ Architecture

Crewzx is a full-stack platform for creating and executing CrewAI workflows with a visual interface and elastic backend that can be deployed on Kubernetes.

## Debugging the Backend

Enable verbose backend logs via environment variables. A ready‑to‑use `.env.debug` file is included for local use.

- Key env vars:
  - `LOG_LEVEL` (default `INFO`): set `DEBUG` for verbosity
  - `LOG_FORMAT` (default `json`): set `pretty` for human‑readable logs
  - `LOG_HTTP` (default `false`): `true` to log each HTTP request
  - `SQL_ECHO` (default `false`): `true` to echo SQL statements
  - `UVICORN_LOG_LEVEL` (default `info`): uvicorn log level (`debug`, `info`, ...)
  - `LOG_DEBUG_MODULES`: comma‑separated modules to force DEBUG (e.g. `sqlalchemy.engine,httpx`)

- With Docker Compose:
  ```bash
  docker compose --env-file ./.env.debug up -d --build backend
  # or override inline
  LOG_LEVEL=DEBUG LOG_FORMAT=pretty LOG_HTTP=true SQL_ECHO=true \
    UVICORN_LOG_LEVEL=debug docker compose up -d --build backend
  ```

- Running backend directly:
  ```bash
  export LOG_LEVEL=DEBUG LOG_FORMAT=pretty LOG_HTTP=true SQL_ECHO=true UVICORN_LOG_LEVEL=debug
  export ALLOWED_ORIGINS=http://localhost:3001,http://localhost:3000
  uvicorn backend.src.main:app --host 0.0.0.0 --port 8000 --reload --log-level "$UVICORN_LOG_LEVEL"
  ```

Notes:
- Do not use `.env.debug` in production; it includes non‑secure defaults for local development.
- CORS is env‑driven; adjust `ALLOWED_ORIGINS`/`ALLOWED_ORIGIN_REGEX` as needed.
