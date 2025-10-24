#!/bin/bash
# Langfuse Deployment Verification Script

set -e

echo "============================================"
echo "Langfuse Deployment Verification"
echo "============================================"
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check functions
check_container() {
    local container=$1
    if docker ps --format '{{.Names}}' | grep -q "^${container}$"; then
        echo -e "${GREEN}✓${NC} Container ${container} is running"
        return 0
    else
        echo -e "${RED}✗${NC} Container ${container} is NOT running"
        return 1
    fi
}

check_url() {
    local url=$1
    local name=$2
    if curl -s -o /dev/null -w "%{http_code}" "${url}" | grep -q "200\|302"; then
        echo -e "${GREEN}✓${NC} ${name} is accessible at ${url}"
        return 0
    else
        echo -e "${RED}✗${NC} ${name} is NOT accessible at ${url}"
        return 1
    fi
}

check_database() {
    local dbname=$1
    if docker exec crewai-postgres psql -U crewai -lqt | cut -d \| -f 1 | grep -qw "${dbname}"; then
        echo -e "${GREEN}✓${NC} Database ${dbname} exists"
        return 0
    else
        echo -e "${RED}✗${NC} Database ${dbname} does NOT exist"
        return 1
    fi
}

check_env_var() {
    local container=$1
    local varname=$2
    if docker exec "${container}" env | grep -q "^${varname}="; then
        local value=$(docker exec "${container}" env | grep "^${varname}=" | cut -d= -f2)
        echo -e "${GREEN}✓${NC} ${container}: ${varname}=${value}"
        return 0
    else
        echo -e "${RED}✗${NC} ${container}: ${varname} is NOT set"
        return 1
    fi
}

# Start verification
echo "1. Checking Docker Containers..."
echo "--------------------------------"
CONTAINERS_OK=true
check_container "crewai-postgres" || CONTAINERS_OK=false
check_container "crewai-backend" || CONTAINERS_OK=false
check_container "crewai-celery-worker" || CONTAINERS_OK=false
check_container "crewai-langfuse-web" || CONTAINERS_OK=false
check_container "crewai-langfuse-worker" || CONTAINERS_OK=false
echo ""

echo "2. Checking Service Accessibility..."
echo "------------------------------------"
SERVICES_OK=true
check_url "http://localhost:8000/health" "Backend API" || SERVICES_OK=false
check_url "http://localhost:3002" "Langfuse UI" || SERVICES_OK=false
echo ""

echo "3. Checking Databases..."
echo "------------------------"
DATABASES_OK=true
check_database "crewai_platform" || DATABASES_OK=false
check_database "langfuse" || DATABASES_OK=false
echo ""

echo "4. Checking Environment Variables..."
echo "------------------------------------"
ENV_OK=true
check_env_var "crewai-backend" "LANGFUSE_ENABLED" || ENV_OK=false
check_env_var "crewai-backend" "LANGFUSE_HOST" || ENV_OK=false
check_env_var "crewai-backend" "LANGFUSE_PUBLIC_KEY" || ENV_OK=false
check_env_var "crewai-backend" "LANGFUSE_SECRET_KEY" || ENV_OK=false
check_env_var "crewai-celery-worker" "LANGFUSE_ENABLED" || ENV_OK=false
echo ""

echo "5. Checking Langfuse Initialization..."
echo "--------------------------------------"
INIT_OK=true
if docker logs crewai-backend 2>&1 | grep -qi "langfuse"; then
    echo -e "${GREEN}✓${NC} Backend has Langfuse-related logs"
else
    echo -e "${YELLOW}⚠${NC} No Langfuse-related logs in backend (may be normal on first startup)"
    INIT_OK=false
fi

if docker logs crewai-langfuse-web 2>&1 | grep -qi "ready"; then
    echo -e "${GREEN}✓${NC} Langfuse web is ready"
else
    echo -e "${YELLOW}⚠${NC} Langfuse web may still be initializing"
    INIT_OK=false
fi
echo ""

# Summary
echo "============================================"
echo "VERIFICATION SUMMARY"
echo "============================================"

if $CONTAINERS_OK && $SERVICES_OK && $DATABASES_OK && $ENV_OK; then
    echo -e "${GREEN}✓ All checks passed!${NC}"
    echo ""
    echo "Next steps:"
    echo "1. Access Langfuse UI: http://localhost:3002"
    echo "2. Create admin account and project"
    echo "3. Generate API keys in Langfuse UI"
    echo "4. Update docker-compose.yml with real API keys"
    echo "5. Restart services: docker-compose restart backend celery-worker"
    echo "6. Run a test execution and verify traces appear in Langfuse"
    exit 0
else
    echo -e "${RED}✗ Some checks failed${NC}"
    echo ""
    echo "Troubleshooting:"
    if ! $CONTAINERS_OK; then
        echo "- Some containers are not running. Start with: docker-compose up -d"
    fi
    if ! $SERVICES_OK; then
        echo "- Some services are not accessible. Check logs: docker-compose logs"
    fi
    if ! $DATABASES_OK; then
        echo "- Langfuse database missing. Check init script: docker logs crewai-postgres"
    fi
    if ! $ENV_OK; then
        echo "- Environment variables not set. Check docker-compose.yml"
    fi
    exit 1
fi
