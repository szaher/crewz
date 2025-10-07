# Crewzx
Crewzx is a project to enable users to chat with LLMs using CrewAI crews and flows. The project aims to create a drag‑and‑drop frontend with an elastic backend that can be deployed on Kubernetes.

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
