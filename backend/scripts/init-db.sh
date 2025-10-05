#!/bin/bash
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    -- Create extensions
    CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

    -- Database is already created by POSTGRES_DB env var
    GRANT ALL PRIVILEGES ON DATABASE crewai_platform TO crewai;

    -- Create a template tenant schema for reference
    CREATE SCHEMA IF NOT EXISTS tenant_template;

    GRANT ALL ON SCHEMA tenant_template TO crewai;
EOSQL

echo "Database initialization complete"
