Run ESLint on the web app and ruff on the Python backend.

Usage: /lint

```bash
echo "=== Python (ruff) ===" && cd /Users/yasin_bulgan/Desktop/Cortex_Ai_Automation/backend && python -m ruff check . 2>&1 | tail -20 && echo "=== TypeScript (eslint) ===" && cd /Users/yasin_bulgan/Desktop/Cortex_Ai_Automation && npm run lint --workspace apps/web 2>&1 | tail -20
```
