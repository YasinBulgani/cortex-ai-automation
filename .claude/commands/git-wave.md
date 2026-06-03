Show recent wave-related commits and test count summary.

Usage: /git-wave

```bash
cd /Users/yasin_bulgan/Desktop/Cortex_Ai_Automation && git log --oneline -20 && echo "---" && echo "Backend unit tests:" && find backend/tests/unit -name "*.py" | wc -l && echo "Backend total tests:" && find backend/tests -name "*.py" | wc -l
```
