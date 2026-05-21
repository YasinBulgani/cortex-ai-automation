#!/bin/bash
set -e

# Colors for output
BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
DB_HOST="${DATABASE_HOST:-db}"
DB_PORT="${DATABASE_PORT:-5432}"
DB_NAME="${DATABASE_NAME:-synthetic_bank}"
DB_USER="${DATABASE_USER:-postgres}"
MAX_RETRIES=30
RETRY_INTERVAL=1

echo -e "${BLUE}Starting SyntheticBankData Application${NC}"

# Function to wait for database
wait_for_db() {
    echo -e "${YELLOW}Waiting for database to be ready...${NC}"
    RETRY_COUNT=0

    while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
        if pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" >/dev/null 2>&1; then
            echo -e "${GREEN}✓ Database is ready${NC}"
            return 0
        fi

        RETRY_COUNT=$((RETRY_COUNT + 1))
        echo "Attempt $RETRY_COUNT/$MAX_RETRIES: Waiting for database..."
        sleep $RETRY_INTERVAL
    done

    echo -e "${RED}✗ Database is not responding after $MAX_RETRIES attempts${NC}"
    exit 1
}

# Function to run migrations
run_migrations() {
    echo -e "${YELLOW}Running database migrations...${NC}"

    if command -v alembic &> /dev/null; then
        alembic upgrade head
        echo -e "${GREEN}✓ Migrations completed${NC}"
    else
        echo -e "${YELLOW}⚠ Alembic not found, skipping migrations${NC}"
    fi
}

# Function to check application health
check_health() {
    echo -e "${YELLOW}Waiting for application to be healthy...${NC}"

    local HEALTH_RETRIES=30
    local HEALTH_INTERVAL=2
    local RETRY=0

    while [ $RETRY -lt $HEALTH_RETRIES ]; do
        if curl -sf http://localhost:8000/health >/dev/null 2>&1; then
            echo -e "${GREEN}✓ Application is healthy${NC}"
            return 0
        fi

        RETRY=$((RETRY + 1))
        echo "Health check attempt $RETRY/$HEALTH_RETRIES..."
        sleep $HEALTH_INTERVAL
    done

    echo -e "${YELLOW}⚠ Application health check timed out (will continue)${NC}"
}

# Main execution
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}Initialization Steps${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# Step 1: Wait for database
wait_for_db

# Step 2: Run migrations
if [ "${RUN_MIGRATIONS:-true}" = "true" ]; then
    run_migrations
fi

# Step 3: Start application
echo -e "${YELLOW}Starting uvicorn application server...${NC}"
exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers "${UVICORN_WORKERS:-4}" \
    --access-log \
    --log-level "${LOG_LEVEL:-info}"
