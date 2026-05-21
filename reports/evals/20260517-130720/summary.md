# Eval Quality Report

- Generated: `2026-05-17T13:07:20.210048+00:00`
- Overall: **PASS**
- Cases: **3/3**
- Total latency: **0 ms**

## Suites

| Suite | Status | Cases | Case Pass Rate | Latency | Metrics |
|---|---:|---:|---:|---:|---|
| ai_gateway_smoke | PASS | 3/3 | 1.000 | 0 ms | gateway_attempts_healthy=1.000, gateway_content_contains=1.000, gateway_json_valid=1.000, gateway_latency_budget=1.000, gateway_provider_allowed=1.000 |

## Cases

| Suite | Case | Status | Latency | Runtime | Scores |
|---|---|---:|---:|---|---|
| ai_gateway_smoke | gw-chat-basic | PASS | 0 ms | ollama / llama3.1:8b / attempts=1 | gateway_content_contains=1.000, gateway_provider_allowed=1.000, gateway_attempts_healthy=1.000, gateway_json_valid=1.000, gateway_latency_budget=1.000 |
| ai_gateway_smoke | gw-failover-attempts | PASS | 0 ms | ollama / llama3.1:8b / attempts=2 | gateway_content_contains=1.000, gateway_provider_allowed=1.000, gateway_attempts_healthy=1.000, gateway_json_valid=1.000, gateway_latency_budget=1.000 |
| ai_gateway_smoke | gw-json-mode | PASS | 0 ms | ollama / qwen2.5:14b / attempts=1 | gateway_content_contains=1.000, gateway_provider_allowed=1.000, gateway_attempts_healthy=1.000, gateway_json_valid=1.000, gateway_latency_budget=1.000 |
