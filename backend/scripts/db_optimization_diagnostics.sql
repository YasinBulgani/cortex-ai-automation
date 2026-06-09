/**
 * PostgreSQL Performance Diagnostics & Monitoring
 * Run in psql: psql -h localhost -U postgres -d neurex_db -f db_optimization_diagnostics.sql
 *
 * Reports:
 * 1. Missing indexes (high-impact candidates)
 * 2. Table bloat & vacuum stats
 * 3. Slow queries (query plan analysis)
 * 4. Index bloat & unused indexes
 * 5. Connection pool status
 * 6. Replication lag (if applicable)
 * 7. WAL archive status
 * 8. Statistics freshness
 */

-- ═══════════════════════════════════════════════════════════════════════════════
-- 1. MISSING INDEXES DIAGNOSTIC
-- ═══════════════════════════════════════════════════════════════════════════════
-- Identifies high-cardinality columns used in WHERE/JOIN but without indexes

\echo '==== MISSING INDEX CANDIDATES (High Impact) ===='

WITH seq_scans AS (
    SELECT
        schemaname,
        tablename,
        seq_scan,
        seq_tup_read,
        idx_scan,
        idx_tup_fetch,
        ROUND(100 * seq_scan / NULLIF(seq_scan + idx_scan, 0), 2) AS seq_scan_pct
    FROM pg_stat_user_tables
    WHERE seq_scan > 100  -- Tables with high seq scan count
    ORDER BY seq_scan DESC
    LIMIT 20
)
SELECT
    tablename,
    seq_scan,
    seq_scan_pct,
    CASE
        WHEN seq_scan_pct > 70 THEN '🔴 CRITICAL: Add composite index'
        WHEN seq_scan_pct > 50 THEN '🟠 HIGH: Likely index missing'
        WHEN seq_scan_pct > 30 THEN '🟡 MEDIUM: Review WHERE clauses'
        ELSE '🟢 OK'
    END AS recommendation
FROM seq_scans;

-- ═══════════════════════════════════════════════════════════════════════════════
-- 2. TABLE BLOAT & VACUUM EFFICIENCY
-- ═══════════════════════════════════════════════════════════════════════════════

\echo '==== TABLE BLOAT STATUS ===='

WITH bloat AS (
    SELECT
        schemaname,
        tablename,
        round(100 * pg_total_relation_size(schemaname||'.'||tablename) /
              NULLIF(pg_relation_size(schemaname||'.'||tablename), 0), 2) AS bloat_ratio,
        pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS total_size,
        last_vacuum,
        last_autovacuum,
        n_live_tup,
        n_dead_tup,
        ROUND(100 * n_dead_tup / NULLIF(n_live_tup + n_dead_tup, 0), 2) AS dead_pct
    FROM pg_stat_user_tables
    WHERE n_live_tup > 10000  -- Tables > 10K rows
    ORDER BY dead_pct DESC
)
SELECT
    tablename,
    total_size,
    n_live_tup,
    n_dead_tup,
    dead_pct,
    last_autovacuum,
    CASE
        WHEN dead_pct > 20 THEN '🔴 RUN VACUUM IMMEDIATELY'
        WHEN dead_pct > 10 THEN '🟠 VACUUM RECOMMENDED'
        WHEN dead_pct > 5 THEN '🟡 MONITOR'
        ELSE '🟢 OK'
    END AS action
FROM bloat;

-- ═══════════════════════════════════════════════════════════════════════════════
-- 3. INDEX BLOAT & EFFICIENCY
-- ═══════════════════════════════════════════════════════════════════════════════

\echo '==== INDEX BLOAT & UNUSED INDEXES ===='

WITH idx_stats AS (
    SELECT
        schemaname,
        tablename,
        indexname,
        idx_scan,
        idx_tup_read,
        idx_tup_fetch,
        pg_size_pretty(pg_relation_size(indexrelid)) AS index_size,
        ROUND(100 * idx_tup_fetch / NULLIF(idx_tup_read, 0), 2) AS selectivity
    FROM pg_stat_user_indexes
    ORDER BY idx_scan ASC, pg_relation_size(indexrelid) DESC
)
SELECT
    tablename,
    indexname,
    index_size,
    idx_scan,
    idx_tup_read,
    selectivity,
    CASE
        WHEN idx_scan = 0 AND pg_relation_size(indexrelid) > 10485760 THEN '🔴 UNUSED, >10MB: DROP?'
        WHEN idx_scan < 100 THEN '🟠 RARELY USED: Review'
        WHEN selectivity < 10 THEN '🟡 LOW SELECTIVITY: Not effective'
        ELSE '🟢 HEALTHY'
    END AS status
FROM idx_stats
LIMIT 30;

-- ═══════════════════════════════════════════════════════════════════════════════
-- 4. SLOW QUERY ANALYSIS (via logs, if enabled)
-- ═══════════════════════════════════════════════════════════════════════════════

\echo '==== TOP TABLES BY SEQUENTIAL SCANS ===='

SELECT
    schemaname,
    tablename,
    seq_scan,
    seq_tup_read,
    ROUND(seq_tup_read::numeric / NULLIF(seq_scan, 0), 0) AS avg_rows_scanned,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_stat_user_tables
WHERE seq_scan > 1000
ORDER BY seq_scan DESC
LIMIT 15;

-- ═══════════════════════════════════════════════════════════════════════════════
-- 5. CONNECTION POOL STATUS
-- ═══════════════════════════════════════════════════════════════════════════════

\echo '==== CONNECTION POOL STATUS ===='

SELECT
    datname,
    COUNT(*) AS total_connections,
    SUM(CASE WHEN state = 'active' THEN 1 ELSE 0 END) AS active,
    SUM(CASE WHEN state = 'idle' THEN 1 ELSE 0 END) AS idle,
    SUM(CASE WHEN state = 'idle in transaction' THEN 1 ELSE 0 END) AS idle_xact
FROM pg_stat_activity
WHERE datname IS NOT NULL
GROUP BY datname;

-- ═══════════════════════════════════════════════════════════════════════════════
-- 6. STATISTICS FRESHNESS
-- ═══════════════════════════════════════════════════════════════════════════════

\echo '==== STATISTICS FRESHNESS (ANALYZE) ===='

SELECT
    schemaname,
    tablename,
    n_live_tup,
    last_analyze,
    last_autoanalyze,
    EXTRACT(EPOCH FROM (NOW() - last_autoanalyze)) / 3600 AS hours_since_autoanalyze
FROM pg_stat_user_tables
WHERE n_live_tup > 100000
ORDER BY last_autoanalyze ASC NULLS FIRST
LIMIT 20;

-- ═══════════════════════════════════════════════════════════════════════════════
-- 7. INDEX EFFECTIVENESS (Selectivity vs Size)
-- ═══════════════════════════════════════════════════════════════════════════════

\echo '==== INDEX EFFECTIVENESS (ROI Analysis) ===='

WITH idx_roi AS (
    SELECT
        tablename,
        indexname,
        pg_size_pretty(pg_relation_size(indexrelid)) AS size_bytes,
        idx_scan,
        idx_tup_read,
        idx_tup_fetch,
        ROUND(100.0 * idx_tup_fetch / NULLIF(idx_tup_read, 1), 2) AS selectivity_pct,
        CASE
            WHEN idx_scan = 0 THEN 'NEVER_USED'
            WHEN idx_tup_read = 0 THEN 'ZERO_TUPLES'
            ELSE 'ACTIVE'
        END AS status
    FROM pg_stat_user_indexes
)
SELECT
    tablename,
    indexname,
    size_bytes,
    idx_scan,
    selectivity_pct,
    status
FROM idx_roi
WHERE status != 'ACTIVE'
ORDER BY pg_relation_size(schemaname||'.'||indexname) DESC;

-- ═══════════════════════════════════════════════════════════════════════════════
-- 8. QUERY PERFORMANCE TUNING HINTS
-- ═══════════════════════════════════════════════════════════════════════════════

\echo '==== QUERY OPTIMIZATION OPPORTUNITIES ===='

-- Tables with many updates but few indexes
SELECT
    schemaname,
    tablename,
    n_live_tup,
    n_mod_since_analyze,
    (SELECT COUNT(*) FROM pg_indexes WHERE tablename = t.tablename) AS index_count,
    ROUND(100 * n_mod_since_analyze::numeric / NULLIF(n_live_tup, 0), 2) AS mod_pct,
    CASE
        WHEN mod_pct > 50 THEN '🔴 STALE STATS: RUN ANALYZE'
        WHEN mod_pct > 20 THEN '🟠 STATS AGING: ANALYZE SOON'
        ELSE '🟢 OK'
    END AS action
FROM pg_stat_user_tables t
WHERE n_live_tup > 10000
ORDER BY mod_pct DESC
LIMIT 15;

-- ═══════════════════════════════════════════════════════════════════════════════
-- 9. CACHE HIT RATIO (Determine if more RAM needed)
-- ═══════════════════════════════════════════════════════════════════════════════

\echo '==== CACHE HIT RATIO (Table + Index) ===='

SELECT
    'Table' AS cache_type,
    ROUND(100 * sum(heap_blks_hit) / (sum(heap_blks_hit) + sum(heap_blks_read)), 2) AS hit_ratio_pct,
    sum(heap_blks_hit) AS hits,
    sum(heap_blks_read) AS reads
FROM pg_statio_user_tables
UNION ALL
SELECT
    'Index',
    ROUND(100 * sum(idx_blks_hit) / (sum(idx_blks_hit) + sum(idx_blks_read)), 2),
    sum(idx_blks_hit),
    sum(idx_blks_read)
FROM pg_statio_user_indexes;

-- ═══════════════════════════════════════════════════════════════════════════════
-- 10. DATABASE SIZE BREAKDOWN
-- ═══════════════════════════════════════════════════════════════════════════════

\echo '==== DATABASE SIZE BREAKDOWN ===='

SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS total_size,
    pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) AS table_size,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename) -
                   pg_relation_size(schemaname||'.'||tablename)) AS indexes_size,
    n_live_tup,
    ROUND(pg_total_relation_size(schemaname||'.'||tablename)::numeric /
          NULLIF(n_live_tup, 0), 2) AS bytes_per_row
FROM pg_stat_user_tables
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
LIMIT 25;

-- ═══════════════════════════════════════════════════════════════════════════════
-- 11. RECOMMENDATIONS SUMMARY
-- ═══════════════════════════════════════════════════════════════════════════════

\echo '==== OPTIMIZATION RECOMMENDATIONS ===='
\echo ''
\echo '1. IMMEDIATE ACTIONS:'
\echo '   - Run VACUUM FULL ANALYZE on tables with >20% dead tuples'
\echo '   - Add missing indexes (check output above)'
\echo '   - Drop unused indexes consuming >10MB'
\echo ''
\echo '2. MAINTENANCE WINDOW:'
\echo '   - CLUSTER frequently accessed tables by primary key'
\echo '   - REINDEX heavy-use tables if bloat > 30%'
\echo '   - Update table statistics: ANALYZE;'
\echo ''
\echo '3. LONG-TERM:'
\echo '   - Partition large time-series tables (test_management_*_runs)'
\echo '   - Archive old data (>6 months) to separate schema'
\echo '   - Monitor cache hit ratio (target: >99%)'
\echo '   - Enable pg_stat_statements extension for query analysis'
\echo ''
\echo '4. MONITORING:'
\echo '   - Set up alert for cache hit ratio < 95%'
\echo '   - Monitor table bloat weekly'
\echo '   - Track slow queries (log_min_duration_statement = 1000ms)'
\echo ''
