#!/bin/bash
#
# PostgreSQL Optimization Suite - Quick Start
# Usage: ./db_optimize.sh [apply|verify|diagnose|monitor]
#
# Commands:
#   apply      - Apply optimization migration (creates indexes, etc.)
#   verify     - Verify all optimizations are installed
#   diagnose   - Run full diagnostic report
#   monitor    - Monitor ongoing performance
#   help       - Show this help message

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-neurex_db}"
DB_USER="${DB_USER:-postgres}"

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check PostgreSQL connection
check_connection() {
    if ! psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "SELECT 1" >/dev/null 2>&1; then
        log_error "Cannot connect to PostgreSQL at $DB_HOST:$DB_PORT/$DB_NAME"
        echo "Set environment variables to override:"
        echo "  DB_HOST, DB_PORT, DB_NAME, DB_USER"
        exit 1
    fi
    log_success "Connected to PostgreSQL"
}

# Apply migration
apply_optimization() {
    log_info "Applying PostgreSQL optimization migration..."

    cd "$PROJECT_ROOT"

    # Check if migration file exists
    if [ ! -f "alembic/versions/20260609_0011_db_optimization_suite.py" ]; then
        log_error "Migration file not found: alembic/versions/20260609_0011_db_optimization_suite.py"
        exit 1
    fi

    log_info "Running: alembic upgrade head"
    alembic upgrade head

    log_success "Migration applied successfully"
    log_info "Next: Run './db_optimize.sh verify' to confirm"
}

# Verify optimizations
verify_optimization() {
    log_info "Verifying optimization installation..."

    check_connection

    # Check indexes
    log_info "Checking indexes..."
    INDEXES=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c "
        SELECT COUNT(*) FROM pg_indexes
        WHERE indexname LIKE 'ix_%' AND indexname NOT LIKE 'ix_sd_%'
            OR indexname IN (
                'ix_sd_users_tenant_email',
                'ix_sd_refresh_tokens_user_expires',
                'ix_sd_api_keys_user_revoked',
                'ix_notifications_user_unread'
            );
    " | tr -d ' ')

    if [ "$INDEXES" -ge 12 ]; then
        log_success "Found $INDEXES optimization indexes (expected: 12+)"
    else
        log_warning "Found only $INDEXES indexes (expected: 12+)"
    fi

    # Check constraints
    log_info "Checking constraints..."
    CONSTRAINTS=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c "
        SELECT COUNT(*) FROM information_schema.table_constraints
        WHERE constraint_name LIKE 'chk_%status%';
    " | tr -d ' ')

    if [ "$CONSTRAINTS" -ge 3 ]; then
        log_success "Found $CONSTRAINTS CHECK constraints (expected: 3+)"
    else
        log_warning "Found only $CONSTRAINTS CHECK constraints (expected: 3+)"
    fi

    # Check FILLFACTOR tuning
    log_info "Checking FILLFACTOR tuning..."
    FILLFACTOR=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c "
        SELECT COUNT(*) FROM pg_class
        WHERE reloptions IS NOT NULL AND reloptions::text LIKE '%fillfactor%';
    " | tr -d ' ')

    if [ "$FILLFACTOR" -ge 4 ]; then
        log_success "Found $FILLFACTOR tables with optimized FILLFACTOR"
    else
        log_warning "Found only $FILLFACTOR tables with FILLFACTOR tuning"
    fi

    log_success "Verification complete"
}

# Run diagnostics
run_diagnostics() {
    log_info "Running full PostgreSQL diagnostics..."

    check_connection

    if [ ! -f "scripts/db_optimization_diagnostics.sql" ]; then
        log_error "Diagnostics script not found: scripts/db_optimization_diagnostics.sql"
        exit 1
    fi

    log_info "Running: psql -f scripts/db_optimization_diagnostics.sql"
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f scripts/db_optimization_diagnostics.sql
}

# Monitor performance (quick check)
monitor_performance() {
    log_info "Monitoring database performance..."

    check_connection

    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "
        \echo '═══════════════════════════════════════════════════════════'
        \echo 'QUICK PERFORMANCE SNAPSHOT'
        \echo '═══════════════════════════════════════════════════════════'

        \echo ''
        \echo 'Cache Hit Ratio (Table):'
        SELECT
            CASE
                WHEN ratio < 0.90 THEN '🔴 CRITICAL'
                WHEN ratio < 0.95 THEN '🟠 WARNING'
                ELSE '🟢 HEALTHY'
            END,
            ROUND(100.0 * ratio, 2)::text || '%' AS hit_ratio
        FROM (
            SELECT
                ROUND(sum(heap_blks_hit)::numeric / (sum(heap_blks_hit) + sum(heap_blks_read)), 2) AS ratio
            FROM pg_statio_user_tables
        ) t;

        \echo ''
        \echo 'Index Usage (Top 10 by scans):'
        SELECT tablename, indexname, idx_scan
        FROM pg_stat_user_indexes
        ORDER BY idx_scan DESC LIMIT 10;

        \echo ''
        \echo 'Table Bloat (Top 10):'
        SELECT
            tablename,
            n_live_tup,
            n_dead_tup,
            ROUND(100 * n_dead_tup::numeric / (n_live_tup + n_dead_tup), 2)::text || '%' AS dead_pct
        FROM pg_stat_user_tables
        WHERE n_live_tup > 1000
        ORDER BY n_dead_tup DESC LIMIT 10;

        \echo ''
        \echo 'Sequential Scans (Top 10):'
        SELECT tablename, seq_scan, seq_tup_read
        FROM pg_stat_user_tables
        WHERE seq_scan > 100
        ORDER BY seq_scan DESC LIMIT 10;
    "
}

# Main command parsing
if [ $# -eq 0 ]; then
    log_error "No command specified"
    echo ""
    echo "Usage: $0 [apply|verify|diagnose|monitor|help]"
    exit 1
fi

case "$1" in
    apply)
        apply_optimization
        ;;
    verify)
        verify_optimization
        ;;
    diagnose)
        run_diagnostics
        ;;
    monitor)
        monitor_performance
        ;;
    help)
        echo "PostgreSQL Optimization Suite - Quick Start"
        echo ""
        echo "Usage: $0 [command]"
        echo ""
        echo "Commands:"
        echo "  apply      - Apply optimization migration (creates indexes, tunes parameters)"
        echo "  verify     - Verify all optimizations are installed"
        echo "  diagnose   - Run full diagnostic report (missing indexes, bloat, etc.)"
        echo "  monitor    - Show quick performance snapshot"
        echo "  help       - Show this help message"
        echo ""
        echo "Environment Variables:"
        echo "  DB_HOST    - PostgreSQL hostname (default: localhost)"
        echo "  DB_PORT    - PostgreSQL port (default: 5432)"
        echo "  DB_NAME    - Database name (default: neurex_db)"
        echo "  DB_USER    - Database user (default: postgres)"
        echo ""
        echo "Examples:"
        echo "  ./db_optimize.sh apply              # Apply migration"
        echo "  ./db_optimize.sh verify             # Verify installation"
        echo "  ./db_optimize.sh diagnose           # Run diagnostics"
        echo "  DB_HOST=prod.example.com ./db_optimize.sh monitor  # Monitor prod"
        ;;
    *)
        log_error "Unknown command: $1"
        echo "Run '$0 help' for usage"
        exit 1
        ;;
esac
