# BGTS Cursor Agent Prompt'lari

Skor: **8.2/10 → 9.3/10** hedefiyle 10 agent prompt.
Her dosyadaki ``` blokunu Cursor'a yapistir.

## Uygulama Sirasi

### Faz 1: Error Handling (paralel calisabilir)
| # | Dosya | Alan | Etki |
|---|-------|------|------|
| 1 | [agent-01](agent-01-ai-router-error-handling.md) | AI Router — 16 raw 500 duzeltme | 6.5→9.0 |
| 2 | [agent-02](agent-02-other-routers-error-handling.md) | 8 router — bare except + logging | 6.5→9.0 |

### Faz 2: Production Readiness (paralel calisabilir)
| # | Dosya | Alan | Etki |
|---|-------|------|------|
| 3 | [agent-03](agent-03-config-hardening.md) | Config guvenlik + .env.example | 7.0→9.0 |
| 4 | [agent-04](agent-04-inmemory-to-db.md) | In-memory → PostgreSQL | 7.0→9.0 |
| 5 | [agent-05](agent-05-graceful-shutdown.md) | Graceful shutdown tamamla | 7.0→9.0 |

### Faz 3: Test Coverage (paralel calisabilir)
| # | Dosya | Alan | Etki |
|---|-------|------|------|
| 6 | [agent-06](agent-06-tspm-tests.md) | TSPM 148 ep → 60+ test | 6.5→9.0 |
| 7 | [agent-07](agent-07-api-testing-tests.md) | API Testing 47 ep → 25+ test | 6.5→9.0 |
| 8 | [agent-08](agent-08-remaining-domain-tests.md) | 6 domain → 30+ test | 6.5→9.0 |

### Faz 4: Documentation (paralel calisabilir)
| # | Dosya | Alan | Etki |
|---|-------|------|------|
| 9 | [agent-09](agent-09-router-docstrings.md) | Tum router'lara Turkce docstring | 6.0→8.5 |
| 10 | [agent-10](agent-10-openapi-enrichment.md) | OpenAPI tag desc + ornekler | 6.0→8.5 |

## Her Faz Sonrasi Dogrulama

```bash
# Python syntax
cd backend && python3 -c "
import ast, pathlib
for f in pathlib.Path('app').rglob('*.py'):
    try: ast.parse(f.read_text())
    except SyntaxError as e: print(f'HATA: {f}: {e}')
print('Bitti')
"

# Testler
cd backend && python3 -m pytest tests/ -v --tb=short -q

# Frontend
cd apps/web && npx tsc --noEmit
```
