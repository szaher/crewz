# crewz Development Guidelines

Auto-generated from all feature plans. Last updated: 2025-10-12

## Active Technologies
- Python 3.11 + FastAPI (async), SQLAlchemy, Alembic, Celery, Redis 7, PostgreSQL 15, MongoDB 6.0, ClickHouse 23.8 (003-we-need-to)
- Python 3.11 (backend), TypeScript/React (frontend) (004-proper-isolation-and)
- PostgreSQL (job metadata, execution results), MongoDB (execution logs), Redis (task queue, pub/sub), S3/local filesystem (artifacts) (004-proper-isolation-and)

## Project Structure
```
src/
tests/
```

## Commands
cd src [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] pytest [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] ruff check .

## Code Style
Python 3.11: Follow standard conventions

## Recent Changes
- 004-proper-isolation-and: Added Python 3.11 (backend), TypeScript/React (frontend)
- 003-we-need-to: Added Python 3.11 + FastAPI (async), SQLAlchemy, Alembic, Celery, Redis 7, PostgreSQL 15, MongoDB 6.0, ClickHouse 23.8

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
