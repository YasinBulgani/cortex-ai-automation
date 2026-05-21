# DEPRECATED - Python POM Katmani

**Bu dizindeki Python Page Object'ler artik aktif olarak kullanilmamaktadir.**

## Neden?

Proje, BDD + AI destekli tek birlesik otomasyon mimarisine gecmektedir:
- **Birincil POM**: `e2e/pages/` (TypeScript + Playwright)
- **BDD Framework**: `e2e/bdd/` (Cucumber + Playwright TS)
- **Locator Repository**: `engine/locators/locator_repository.json`

## Goc Durumu

| Python POM | TypeScript Karsiligi | Durum |
|------------|---------------------|--------|
| `login_page.py` | `e2e/pages/login.page.ts` | Tasinmis |
| `projects_page.py` | `e2e/pages/projects.page.ts` | Tasinmis |
| `scenarios_page.py` | `e2e/pages/scenarios-list.page.ts` | Tasinmis |
| `executions_page.py` | `e2e/pages/executions.page.ts` | Tasinmis |
| `flows_page.py` | `e2e/pages/flows.page.ts` | Tasinmis |
| `approvals_page.py` | `e2e/pages/approvals.page.ts` | Tasinmis |
| `import_page.py` | `e2e/pages/import.page.ts` | Tasinmis |
| `regression_page.py` | `e2e/pages/regression.page.ts` | Tasinmis |
| `dashboard_page.py` | (dahili) | POM icinde |
| `common_nav.py` | `e2e/pages/components/sidebar.component.ts` | Tasinmis |

## Ne Zaman Silinecek?

TS POM'un %100 kapsama ulastigi ve engine/tests/e2e/ testlerinin
TS tarafina tamamen tasindigiconfirm edildikten sonra silinecektir.
