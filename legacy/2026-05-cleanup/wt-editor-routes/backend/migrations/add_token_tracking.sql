-- Migration: Add token usage tracking columns to llm_traces
-- Safe to run multiple times (IF NOT EXISTS)

ALTER TABLE llm_traces ADD COLUMN IF NOT EXISTS prompt_tokens INTEGER;
ALTER TABLE llm_traces ADD COLUMN IF NOT EXISTS completion_tokens INTEGER;
ALTER TABLE llm_traces ADD COLUMN IF NOT EXISTS total_tokens INTEGER;

-- Index for cost analysis queries
CREATE INDEX IF NOT EXISTS idx_llm_traces_tokens
    ON llm_traces (agent_name, created_at)
    WHERE total_tokens IS NOT NULL;

-- Index for per-user rate limit queries (if user_id column exists)
-- ALTER TABLE llm_traces ADD COLUMN IF NOT EXISTS user_id VARCHAR(64);
-- CREATE INDEX IF NOT EXISTS idx_llm_traces_user ON llm_traces (user_id, created_at);

-- Summary view for token cost analysis
CREATE OR REPLACE VIEW llm_token_summary AS
SELECT
    model,
    agent_name,
    DATE(created_at) AS day,
    COUNT(*) AS call_count,
    SUM(total_tokens) AS total_tokens,
    SUM(prompt_tokens) AS total_prompt_tokens,
    SUM(completion_tokens) AS total_completion_tokens,
    ROUND(AVG(latency_ms)) AS avg_latency_ms,
    COUNT(*) FILTER (WHERE success = TRUE) AS success_count,
    COUNT(*) FILTER (WHERE success = FALSE) AS failure_count
FROM llm_traces
WHERE created_at > NOW() - INTERVAL '30 days'
GROUP BY model, agent_name, DATE(created_at)
ORDER BY day DESC, total_tokens DESC NULLS LAST;
