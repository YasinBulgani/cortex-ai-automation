-- Migration: Heal history tracking table
-- Safe to run multiple times (IF NOT EXISTS)

CREATE TABLE IF NOT EXISTS heal_history (
    id SERIAL PRIMARY KEY,
    run_id VARCHAR(64),
    test_file VARCHAR(512),
    test_name VARCHAR(256),
    broken_selector TEXT NOT NULL,
    healed_selector TEXT,
    strategy VARCHAR(32),  -- zero-cost, cached, llm, playwright-verified
    tier VARCHAR(16),      -- zero-cost, cached, llm, live
    confidence REAL DEFAULT 0.0,
    stability_score INTEGER DEFAULT 0,
    verified BOOLEAN DEFAULT FALSE,
    file_updated BOOLEAN DEFAULT FALSE,
    root_cause TEXT,
    dom_snippet TEXT,
    heal_duration_ms INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_heal_history_run
    ON heal_history (run_id, created_at);

CREATE INDEX IF NOT EXISTS idx_heal_history_file
    ON heal_history (test_file);

CREATE INDEX IF NOT EXISTS idx_heal_history_strategy
    ON heal_history (strategy, created_at);

-- Playwright MCP sessions table
CREATE TABLE IF NOT EXISTS playwright_sessions (
    id VARCHAR(64) PRIMARY KEY,
    status VARCHAR(16) DEFAULT 'active',  -- active, idle, closed
    current_url TEXT,
    page_title VARCHAR(512),
    headless BOOLEAN DEFAULT TRUE,
    viewport_width INTEGER DEFAULT 1280,
    viewport_height INTEGER DEFAULT 720,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_active_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    closed_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX IF NOT EXISTS idx_playwright_sessions_status
    ON playwright_sessions (status)
    WHERE status = 'active';

-- Summary view for heal stats
CREATE OR REPLACE VIEW heal_stats_summary AS
SELECT
    DATE(created_at) AS day,
    COUNT(*) AS total_attempts,
    COUNT(*) FILTER (WHERE healed_selector IS NOT NULL) AS healed,
    COUNT(*) FILTER (WHERE verified = TRUE) AS verified,
    COUNT(*) FILTER (WHERE file_updated = TRUE) AS files_updated,
    ROUND(AVG(confidence)::numeric, 2) AS avg_confidence,
    ROUND(AVG(heal_duration_ms)) AS avg_duration_ms,
    -- Strategy breakdown
    COUNT(*) FILTER (WHERE strategy = 'zero-cost') AS zero_cost_count,
    COUNT(*) FILTER (WHERE strategy = 'cached') AS cached_count,
    COUNT(*) FILTER (WHERE strategy = 'llm') AS llm_count,
    COUNT(*) FILTER (WHERE strategy = 'playwright-verified') AS pw_verified_count
FROM heal_history
WHERE created_at > NOW() - INTERVAL '30 days'
GROUP BY DATE(created_at)
ORDER BY day DESC;
