Run the backend unit tests (pure helper tests, no DB/Redis needed).

Usage: /test-unit [module_pattern]

```bash
cd /Users/yasin_bulgan/Desktop/Cortex_Ai_Automation/backend && python -m pytest tests/unit/ -v $ARGUMENTS 2>&1 | tail -40
```
