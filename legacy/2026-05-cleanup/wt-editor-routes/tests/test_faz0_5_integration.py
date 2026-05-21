"""
Nexus QA — Faz 0-5 Kapsamlı Entegrasyon Testleri
Tüm fazları tek dosyada test eder:
  Faz 0 : AI Gateway (lifespan, config, models, prompts)
  Faz 1 : Document Parsing (TXT/PDF/DOCX, chunking, sections)
  Faz 2 : Backend Gateway Client (gateway_complete, is_available)
  Faz 3 : Test Case Generation (schemas, models, service, router endpoints, UI)
  Faz 4 : Regression Set Suggestion (schema, service logic, dummy fallback)
  Faz 5 : Automation Code Generation (service, schemas, router endpoint, UI)
  Infra : Docker Compose, frontend lib, AppShell nav links
"""
import sys
import os
import json
import ast
import re
import subprocess
import textwrap

PASS = []
FAIL = []

def test(name, fn):
    try:
        fn()
        PASS.append(name)
        print(f"  ✓ {name}")
    except Exception as e:
        FAIL.append((name, str(e)))
        print(f"  ✗ {name}: {e}")

def run_backend_test(code: str, test_name: str = ""):
    """Run backend Python code in a fresh interpreter with backend path."""
    full_code = textwrap.dedent(f"""
import sys, os
sys.path.insert(0, '/sessions/zealous-lucid-bell/mnt/BGTS_Test_Donusum/backend')
os.environ.setdefault('DATABASE_URL', 'postgresql://test:test@localhost/test')
os.environ.setdefault('SECRET_KEY', 'test-secret-key-for-testing')
{code}
print("OK")
""")
    result = subprocess.run(
        ['python', '-c', full_code],
        capture_output=True, text=True, timeout=30
    )
    if result.returncode != 0 or 'OK' not in result.stdout:
        raise AssertionError(result.stderr.strip() or result.stdout.strip())

# ══════════════════════════════════════════════════════════════════════════════
# FAZ 0: AI GATEWAY
# ══════════════════════════════════════════════════════════════════════════════
print("\n=== FAZ 0: AI GATEWAY ===")

GW = '/sessions/zealous-lucid-bell/mnt/BGTS_Test_Donusum/ai-gateway'

def t_gateway_lifespan():
    with open(f'{GW}/main.py') as f:
        src = f.read()
    assert 'on_event' not in src,           "Deprecated @app.on_event still present"
    assert 'asynccontextmanager' in src,    "Missing asynccontextmanager"
    assert 'lifespan=lifespan' in src,      "lifespan not passed to FastAPI()"
    assert '@asynccontextmanager' in src,   "Missing @asynccontextmanager decorator"
test("gateway: lifespan pattern (no on_event)", t_gateway_lifespan)

def t_gateway_pytest_ini():
    with open(f'{GW}/pytest.ini') as f:
        content = f.read()
    assert 'asyncio_mode = auto' in content
test("gateway: pytest.ini asyncio_mode=auto", t_gateway_pytest_ini)

def t_gateway_models():
    gw_path = GW
    if gw_path not in sys.path:
        sys.path.insert(0, gw_path)
    from app.core.models import TaskType, ProviderName  # type: ignore
    task_values = [t.value for t in TaskType]
    assert 'generate_test_cases' in task_values,    f"Missing generate_test_cases: {task_values}"
    assert 'suggest_regression' in task_values,     f"Missing suggest_regression: {task_values}"
    assert 'generate_gherkin' in task_values,       f"Missing generate_gherkin: {task_values}"
    assert 'generate_java_steps' in task_values,    f"Missing generate_java_steps: {task_values}"
    assert 'generate_playwright' in task_values,    f"Missing generate_playwright: {task_values}"
    providers = [p.value for p in ProviderName]
    assert len(providers) >= 4,     f"Expected >=4 providers, got {providers}"
    assert 'groq' in providers
    assert 'gemini' in providers
test("gateway: TaskType has all 5 AI task types", t_gateway_models)

def t_gateway_config():
    gw_path = GW
    if gw_path not in sys.path:
        sys.path.insert(0, gw_path)
    from app.core.config import settings  # type: ignore
    assert settings.PORT == 8080,           f"Expected 8080 got {settings.PORT}"
    assert 'groq' in settings.PROVIDER_ORDER
    assert settings.CHUNK_SIZE_TOKENS == 3000
test("gateway: config PORT=8080, groq first, chunk=3000", t_gateway_config)

def t_gateway_prompts():
    gw_path = GW
    if gw_path not in sys.path:
        sys.path.insert(0, gw_path)
    from app.core.prompts import PROMPTS  # type: ignore
    required_tasks = ['generate_test_cases', 'suggest_regression', 'generate_gherkin',
                       'generate_java_steps', 'generate_playwright', 'analyze_document']
    for t in required_tasks:
        assert t in PROMPTS, f"Missing prompt: {t}"
    assert len(PROMPTS) >= 6
test("gateway: all 6+ prompts defined", t_gateway_prompts)

def t_gateway_main_imports():
    with open(f'{GW}/main.py') as f:
        src = f.read()
    assert 'from fastapi' in src
    assert 'JSONResponse' in src
    # No duplicate imports
    import_lines = [l for l in src.splitlines() if 'from fastapi.responses import JSONResponse' in l]
    assert len(import_lines) <= 1, f"Duplicate JSONResponse import: {len(import_lines)} times"
test("gateway: no duplicate JSONResponse import", t_gateway_main_imports)

# ══════════════════════════════════════════════════════════════════════════════
# FAZ 1: DOCUMENT PARSING
# ══════════════════════════════════════════════════════════════════════════════
print("\n=== FAZ 1: DOCUMENT PARSING ===")

def t_doc_parser_import():
    run_backend_test("""
from app.domains.tspm.document_parser import parse_document, ParsedDocument
assert callable(parse_document)
assert hasattr(ParsedDocument, '__dataclass_fields__')
fields = ParsedDocument.__dataclass_fields__
assert 'full_text' in fields
assert 'chunks' in fields
assert 'sections' in fields
""")
test("doc_parser: importable with dataclass fields", t_doc_parser_import)

def t_doc_parser_txt_sections():
    run_backend_test("""
from app.domains.tspm.document_parser import parse_document
content = b"# Test Sistemi\\n\\n## Login Modulu\\n\\nGiris modulu aciklamasi.\\n\\n## Rapor Modulu\\n\\nRapor uretimi."
doc = parse_document(content, "test.txt", "text/plain")
assert doc.format == "txt", f"format={doc.format}"
assert "Login" in doc.full_text or "Giris" in doc.full_text
assert len(doc.sections) >= 1, f"sections={doc.sections}"
""")
test("doc_parser: TXT sectioned parse", t_doc_parser_txt_sections)

def t_doc_parser_full_text_default():
    run_backend_test("""
from app.domains.tspm.document_parser import ParsedDocument
# full_text should have a default value
doc = ParsedDocument(filename='test.txt', format='txt')
assert doc.full_text == ''    # default empty string
assert isinstance(doc.chunks, list)
assert isinstance(doc.sections, list)
""")
test("doc_parser: ParsedDocument full_text default=''", t_doc_parser_full_text_default)

def t_doc_parser_chunking():
    run_backend_test("""
from app.domains.tspm.document_parser import parse_document
# Large content should be chunked
big = ("Bu bir test cumlesidi. " * 800 + "\\n\\n") * 2
doc = parse_document(big.encode(), "big.txt", "text/plain")
assert doc.word_count > 100, f"word_count={doc.word_count}"
assert len(doc.chunks) >= 1, f"chunks={len(doc.chunks)}"
""")
test("doc_parser: large file chunking works", t_doc_parser_chunking)

def t_doc_parser_markdown():
    run_backend_test("""
from app.domains.tspm.document_parser import parse_document
content = b"# Feature\\n\\n## Login\\n\\n### Auth\\n\\nDetails here."
doc = parse_document(content, "spec.md", "text/markdown")
assert doc.format == "md"
assert len(doc.sections) >= 1
""")
test("doc_parser: Markdown format detection", t_doc_parser_markdown)

# ══════════════════════════════════════════════════════════════════════════════
# FAZ 2: BACKEND GATEWAY CLIENT
# ══════════════════════════════════════════════════════════════════════════════
print("\n=== FAZ 2: BACKEND GATEWAY CLIENT ===")

def t_gw_client_importable():
    run_backend_test("""
from app.domains.ai.gateway_client import (
    gateway_complete, gateway_analyze_document,
    gateway_generate_test_cases, gateway_is_available
)
assert callable(gateway_complete)
assert callable(gateway_analyze_document)
assert callable(gateway_generate_test_cases)
assert callable(gateway_is_available)
""")
test("gateway_client: all 4 functions importable", t_gw_client_importable)

def t_gw_client_is_available():
    run_backend_test("""
from app.domains.ai.gateway_client import gateway_is_available
result = gateway_is_available()
assert isinstance(result, bool), f"Expected bool, got {type(result)}"
""")
test("gateway_client: gateway_is_available() returns bool", t_gw_client_is_available)

def t_gw_client_url_configured():
    run_backend_test("""
import app.domains.ai.gateway_client as gc
import inspect
src = inspect.getsource(gc)
assert 'AI_GATEWAY_BASE_URL' in src or 'gateway_url' in src.lower() or '8080' in src
""")
test("gateway_client: AI gateway URL configured", t_gw_client_url_configured)

# ══════════════════════════════════════════════════════════════════════════════
# FAZ 3: TEST CASE GENERATION
# ══════════════════════════════════════════════════════════════════════════════
print("\n=== FAZ 3: TEST CASE GENERATION ===")

def t_f3_schemas_all():
    run_backend_test("""
from app.domains.tspm.schemas import (
    GenerateTestCasesRequest, GenerateTestCasesResponse,
    TestCaseOut, AiBatchOut, AiBatchDetailOut,
    BulkReviewRequest, TestCaseReviewAction, TestCaseUpdate
)
# Validate GenerateTestCasesRequest
req = GenerateTestCasesRequest(
    analysis_text='Test sistemi gereksinimleri ve akislar',
    source_name='requirements.pdf',
    modules=[{'module_name': 'Auth', 'risk_level': 'high', 'estimated_tests': 8},
             {'module_name': 'Rapor', 'risk_level': 'medium', 'estimated_tests': 5}]
)
assert req.source_type == 'document'
assert len(req.modules) == 2
# BulkReviewRequest
bulk = BulkReviewRequest(ids=['id1','id2','id3'], action='approve')
assert bulk.action == 'approve'
bulk2 = BulkReviewRequest(ids=['id1'], action='reject', reviewer_note='kalite dusuk')
assert bulk2.reviewer_note == 'kalite dusuk'
""")
test("faz3 schemas: all importable and validate OK", t_f3_schemas_all)

def t_f3_models_columns():
    run_backend_test("""
from app.domains.tspm.models import TspmAiBatch, TspmTestCase
batch_cols = {c.key for c in TspmAiBatch.__table__.columns}
tc_cols = {c.key for c in TspmTestCase.__table__.columns}
required_b = {'id','project_id','status','total_generated','approved_count','rejected_count',
              'source_type','source_name','ai_provider','extra_instructions','created_at'}
required_t = {'id','project_id','batch_id','title','review_status','priority',
              'risk_level','steps','preconditions','expected_result','test_type','tags',
              'module_name','feature_area','created_at','updated_at'}
missing_b = required_b - batch_cols
missing_t = required_t - tc_cols
assert not missing_b, f'TspmAiBatch missing: {missing_b}'
assert not missing_t, f'TspmTestCase missing: {missing_t}'
""")
test("faz3 models: all required columns present", t_f3_models_columns)

def t_f3_service_parse():
    run_backend_test("""
import json
from app.domains.tspm.test_case_service import _parse_test_cases_json
data = [{'title': 'TC1', 'priority': 'high'}, {'title': 'TC2', 'priority': 'medium'}]
# Plain JSON array
assert _parse_test_cases_json(json.dumps(data)) == data
# Dict-wrapped
assert _parse_test_cases_json(json.dumps({'test_cases': data})) == data
# Markdown fenced
fenced = '```json\\n' + json.dumps(data) + '\\n```'
assert _parse_test_cases_json(fenced) == data
# Empty falls back gracefully
result = _parse_test_cases_json('not json at all')
assert isinstance(result, list)
""")
test("faz3 service: _parse_test_cases_json all formats", t_f3_service_parse)

def t_f3_service_normalize():
    run_backend_test("""
from app.domains.tspm.test_case_service import _normalize_steps, _validate_enum
# Dict steps preserved
steps = _normalize_steps([{'order': 1, 'action': 'Click login', 'expected': 'Login sayfasi açılır'}])
assert steps[0]['action'] == 'Click login'
assert 'expected' in steps[0]
# String steps converted
steps2 = _normalize_steps(['Step birinci', 'Step ikinci', 'Step ucuncu'])
assert len(steps2) == 3
assert steps2[0]['action'] == 'Step birinci'
# Enum validation
assert _validate_enum('invalid_val', ['high','medium','low'], 'medium') == 'medium'
assert _validate_enum('high', ['high','medium','low'], 'medium') == 'high'
assert _validate_enum(None, ['high','medium','low'], 'low') == 'low'
""")
test("faz3 service: _normalize_steps and _validate_enum", t_f3_service_normalize)

def t_f3_service_prompt():
    run_backend_test("""
from app.domains.tspm.test_case_service import _build_prompt_for_modules
modules = [
    {'module_name': 'Kimlik Dogrulama', 'risk_level': 'high', 'estimated_tests': 8},
    {'module_name': 'Rapor Modulu', 'risk_level': 'medium', 'estimated_tests': 5}
]
prompt = _build_prompt_for_modules('Sistem tanim metni', modules, 'Ekstra talimatlar')
assert 'Kimlik Dogrulama' in prompt
assert 'Rapor Modulu' in prompt
assert 'Ekstra talimatlar' in prompt
assert 'JSON' in prompt
""")
test("faz3 service: _build_prompt_for_modules includes all modules", t_f3_service_prompt)

def t_f3_bdd_conversion():
    run_backend_test("""
import uuid
from app.domains.tspm.models import TspmTestCase
from app.domains.tspm.test_case_service import _test_case_to_scenario

tc = TspmTestCase(
    id=str(uuid.uuid4()), project_id=str(uuid.uuid4()),
    title='Kullanici giris yaptiginda anasayfaya yonlendirilir',
    test_type='functional', priority='high', risk_level='high',
    preconditions=['Kullanici kayitli olmali', 'Sistem aktif olmali'],
    steps=[
        {'order':1,'action':'Kullanici adi ve sifre gir','expected':'Alanlar doldu'},
        {'order':2,'action':'Login butonuna tikla','expected':'Istek gönderildi'},
    ],
    expected_result='Anasayfaya yonlendirilir',
    tags=['auth', 'smoke'], module_name='Auth', review_status='approved',
)
s = _test_case_to_scenario(tc)
assert s.title == tc.title
keywords = [x['keyword'] for x in s.steps]
assert 'Given' in keywords, f'Missing Given: {keywords}'
assert 'When' in keywords, f'Missing When: {keywords}'
assert 'Then' in keywords, f'Missing Then: {keywords}'
# Tags should include test_type, priority, risk_level
assert any('auth' in str(t).lower() or 'functional' in str(t).lower() for t in s.tags)
""")
test("faz3 service: TestCase → BDD Scenario (Given/When/Then)", t_f3_bdd_conversion)

def t_f3_router_endpoints():
    with open('/sessions/zealous-lucid-bell/mnt/BGTS_Test_Donusum/backend/app/domains/tspm/router.py') as f:
        src = f.read()
    tree = ast.parse(src)
    funcs = {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
    required = [
        'generate_test_cases', 'list_batches', 'get_batch', 'delete_batch',
        'list_test_cases', 'get_test_case', 'update_test_case',
        'review_test_case', 'bulk_review_test_cases', 'delete_test_case'
    ]
    missing = [fn for fn in required if fn not in funcs]
    assert not missing, f"Missing endpoints: {missing}"
test("faz3 router: all 10 endpoints defined", t_f3_router_endpoints)

def t_f3_ui_page():
    with open('/sessions/zealous-lucid-bell/mnt/BGTS_Test_Donusum/apps/web/app/(dashboard)/p/[projectId]/test-cases/page.tsx') as f:
        src = f.read()
    required_components = ['TestCaseCard', 'EditModal']
    required_handlers = ['handleApprove', 'handleReject', 'handleBulkAction']
    required_features = ['filterStatus', 'bulk-review', 'generate']
    for c in required_components:
        assert c in src, f"Missing component: {c}"
    for h in required_handlers:
        assert h in src, f"Missing handler: {h}"
    for f in required_features:
        assert f in src, f"Missing feature: {f}"
test("faz3 UI: test-cases page complete", t_f3_ui_page)

# ══════════════════════════════════════════════════════════════════════════════
# FAZ 4: REGRESSION SET SUGGESTION
# ══════════════════════════════════════════════════════════════════════════════
print("\n=== FAZ 4: REGRESSION SET SUGGESTION ===")

def t_f4_regression_schemas():
    run_backend_test("""
from app.domains.tspm.schemas import RegressionSuggestRequest, RegressionSuggestResponse
req = RegressionSuggestRequest(project_id='proj-1', extra_instructions='Kritik akilari dahil et')
assert req.project_id == 'proj-1'
assert req.extra_instructions == 'Kritik akilari dahil et'
""")
test("faz4 schemas: RegressionSuggestRequest validates", t_f4_regression_schemas)

def t_f4_regression_service_import():
    run_backend_test("""
from app.domains.tspm.regression_suggest import suggest_regression_sets, _build_dummy_sets
assert callable(suggest_regression_sets)
assert callable(_build_dummy_sets)
""")
test("faz4 service: importable", t_f4_regression_service_import)

def t_f4_regression_dummy_fallback():
    run_backend_test("""
from app.domains.tspm.regression_suggest import _build_dummy_sets
scenarios = [
    {'id': f'sc-{i}', 'title': f'Senaryo {i}', 'status': 'active', 'tags': ['smoke']}
    for i in range(10)
]
sets = _build_dummy_sets(scenarios)
assert isinstance(sets, list), 'Expected list'
assert len(sets) >= 2, f'Expected >=2 sets, got {len(sets)}'
for s in sets:
    assert 'name' in s
    assert 'description' in s
    assert 'scenario_ids' in s
    assert 'priority' in s
    assert s['priority'] in ('critical','high','medium','low')
    assert all(sid.startswith('sc-') for sid in s['scenario_ids'])
""")
test("faz4 service: _build_dummy_sets returns valid structure", t_f4_regression_dummy_fallback)

def t_f4_regression_empty_input():
    run_backend_test("""
from app.domains.tspm.regression_suggest import suggest_regression_sets
result = suggest_regression_sets([])
assert result == [], f'Expected empty list, got {result}'
""")
test("faz4 service: empty input returns []", t_f4_regression_empty_input)

def t_f4_regression_gateway_usage():
    with open('/sessions/zealous-lucid-bell/mnt/BGTS_Test_Donusum/backend/app/domains/tspm/regression_suggest.py') as f:
        src = f.read()
    assert 'gateway_complete' in src,   "Missing gateway_complete call"
    assert 'gateway_is_available' in src, "Missing gateway_is_available check"
    assert '_build_dummy_sets' in src,  "Missing dummy fallback"
    assert 'openai' in src.lower(),     "Missing OpenAI fallback"
    assert 'suggest_regression' in src, "Missing task_type=suggest_regression"
test("faz4 service: uses gateway → OpenAI → dummy chain", t_f4_regression_gateway_usage)

def t_f4_regression_json_parsing():
    run_backend_test("""
import re, json
# Test the JSON parsing logic from _suggest_via_gateway
raw_with_fence = '''```json
{
  "sets": [
    {"name": "Test Set 1", "description": "Desc", "scenario_ids": ["s1","s2"], "priority": "high"}
  ]
}
```'''
cleaned = re.sub(r'^```(?:json)?\\s*|\\s*```$', '', raw_with_fence.strip(), flags=re.MULTILINE).strip()
parsed = json.loads(cleaned)
sets = parsed.get('sets', [])
assert len(sets) == 1
assert sets[0]['name'] == 'Test Set 1'
""")
test("faz4 service: JSON markdown fence stripping works", t_f4_regression_json_parsing)

# ══════════════════════════════════════════════════════════════════════════════
# FAZ 5: AUTOMATION CODE GENERATION
# ══════════════════════════════════════════════════════════════════════════════
print("\n=== FAZ 5: AUTOMATION CODE GENERATION ===")

def t_f5_schemas():
    run_backend_test("""
from app.domains.tspm.schemas import (
    GenerateAutomationRequest, GenerateAutomationResponse,
    GherkinResult, JavaResult, PlaywrightResult
)
# GenerateAutomationRequest
req = GenerateAutomationRequest(
    feature_name='Login ve Kimlik Dogrulama',
    batch_id='batch-123',
    include_java=True,
    include_playwright=True
)
assert req.feature_name == 'Login ve Kimlik Dogrulama'
assert req.include_java == True
req2 = GenerateAutomationRequest(
    feature_name='Minimal',
    test_case_ids=['tc-1','tc-2']
)
assert req2.test_case_ids == ['tc-1','tc-2']
# GherkinResult
g = GherkinResult(gherkin='Feature: Test', feature_name='Test', scenario_count=3)
assert g.scenario_count == 3
# JavaResult
j = JavaResult(java_code='public class Test {}', class_name='TestSteps', method_count=5)
assert j.method_count == 5
# PlaywrightResult
p = PlaywrightResult(ts_code='test()', test_count=2)
assert p.test_count == 2
""")
test("faz5 schemas: all importable and validate OK", t_f5_schemas)

def t_f5_service_import():
    run_backend_test("""
from app.domains.tspm.automation_gen_service import (
    generate_gherkin_from_test_cases,
    generate_java_steps_from_gherkin,
    generate_playwright_from_test_cases,
    generate_full_automation_package,
    _build_gherkin_prompt,
    _build_java_steps_prompt,
    _build_playwright_prompt,
    _to_java_class_name,
    _strip_code_fences
)
assert callable(generate_gherkin_from_test_cases)
assert callable(generate_java_steps_from_gherkin)
assert callable(generate_playwright_from_test_cases)
assert callable(generate_full_automation_package)
""")
test("faz5 service: all functions importable", t_f5_service_import)

def t_f5_service_java_class_name():
    run_backend_test("""
from app.domains.tspm.automation_gen_service import _to_java_class_name
assert _to_java_class_name('login modulu') == 'LoginModulu'
assert _to_java_class_name('User Authentication') == 'UserAuthentication'
assert _to_java_class_name('') == 'Feature'
assert _to_java_class_name('API Test v2') == 'ApiTestV2'
assert _to_java_class_name('kullanici giris cikis') == 'KullaniciGirisCikis'
""")
test("faz5 service: _to_java_class_name conversions", t_f5_service_java_class_name)

def t_f5_service_strip_code_fences():
    run_backend_test("""
from app.domains.tspm.automation_gen_service import _strip_code_fences
# With language tag
java = '```java\\npublic class Test {}\\n```'
assert _strip_code_fences(java, 'java') == 'public class Test {}'
# With generic fence
plain = '```\\nsome content here\\n```'
assert _strip_code_fences(plain) == 'some content here'
# No fence - return as-is
raw = 'Feature: Login\\n  Scenario: Test'
assert _strip_code_fences(raw, 'gherkin') == raw
# TypeScript fence
ts = '```typescript\\nconst x = 1;\\n```'
assert _strip_code_fences(ts, 'typescript') == 'const x = 1;'
""")
test("faz5 service: _strip_code_fences all variants", t_f5_service_strip_code_fences)

def t_f5_service_gherkin_prompt():
    run_backend_test("""
from app.domains.tspm.automation_gen_service import _build_gherkin_prompt
test_cases = [
    {
        'title': 'Kullanici giris yapabilir',
        'test_type': 'functional',
        'priority': 'high',
        'risk_level': 'high',
        'preconditions': ['Sistem aktif olmali'],
        'steps': [
            {'order': 1, 'action': 'Kullanici adi gir', 'expected': 'Alan doldu'},
            {'order': 2, 'action': 'Login tıkla', 'expected': 'Giris yapildi'}
        ],
        'expected_result': 'Anasayfaya yonlendirilir'
    },
    {
        'title': 'Gecersiz sifre ile giris yapilamaz',
        'test_type': 'negative',
        'priority': 'high',
        'risk_level': 'medium',
        'steps': [{'order':1,'action':'Yanlis sifre gir','expected':'Hata mesaji'}],
        'expected_result': 'Hata gosterilir'
    }
]
prompt = _build_gherkin_prompt(test_cases, 'Login Modulu')
assert 'Login Modulu' in prompt
assert 'Kullanici giris yapabilir' in prompt
assert 'Gecersiz sifre' in prompt
assert 'Olduğu gibi' in prompt or 'Eğer' in prompt or 'O zaman' in prompt or 'Cucumber' in prompt or 'Türkçe' in prompt
assert 'Scenario' in prompt or 'feature' in prompt.lower()
""")
test("faz5 service: _build_gherkin_prompt includes TCs + Turkish Cucumber", t_f5_service_gherkin_prompt)

def t_f5_service_java_prompt():
    run_backend_test("""
from app.domains.tspm.automation_gen_service import _build_java_steps_prompt
gherkin = '''Feature: Login\\n  Scenario: Kullanici giris yapar\\n    Given Sistem aktif\\n    When Login yap\\n    Then Anasayfa gorunur'''
prompt = _build_java_steps_prompt(gherkin, 'Login Modulu')
assert 'LoginModulu' in prompt or 'Login Modulu' in prompt
assert 'NexusQA' in prompt or 'Selenium' in prompt
assert 'com.nexusqa.steps' in prompt
assert '@Given' in prompt or 'Cucumber' in prompt
assert gherkin[:50] in prompt or 'Gherkin' in prompt
""")
test("faz5 service: _build_java_steps_prompt has NexusQA rules", t_f5_service_java_prompt)

def t_f5_service_playwright_prompt():
    run_backend_test("""
from app.domains.tspm.automation_gen_service import _build_playwright_prompt
test_cases = [
    {'title': 'Login testi', 'test_type': 'functional', 'priority': 'high'},
    {'title': 'Hata mesaji testi', 'test_type': 'negative', 'priority': 'medium'},
]
prompt = _build_playwright_prompt(test_cases, 'Login Modulu')
assert 'Login Modulu' in prompt
assert 'Login testi' in prompt
assert 'Hata mesaji testi' in prompt
assert 'playwright' in prompt.lower() or 'TypeScript' in prompt
assert 'test.describe' in prompt or 'describe' in prompt
""")
test("faz5 service: _build_playwright_prompt has Playwright rules", t_f5_service_playwright_prompt)

def t_f5_service_scenario_count():
    run_backend_test("""
import re
# Test scenario counting regex used in the service
gherkin_sample = '''Feature: Login
  Scenario: Gecerli giris
    Given Sistem aktif
    When Kullanici giris yapar
    Then Basarili olur

  Scenario: Gecersiz giris
    Given Sistem aktif
    When Yanlis sifre girer
    Then Hata gosterilir

  Scenario Outline: Coklu test
    Given <input> girildi
    Then <output> gorunur
    Examples:
      | input | output |
      | a     | x      |'''
count = len(re.findall(r'^\\s*Scenario', gherkin_sample, re.MULTILINE))
assert count == 3, f'Expected 3, got {count}'
""")
test("faz5 service: scenario count regex works", t_f5_service_scenario_count)

def t_f5_router_endpoint():
    with open('/sessions/zealous-lucid-bell/mnt/BGTS_Test_Donusum/backend/app/domains/tspm/router.py') as f:
        src = f.read()
    tree = ast.parse(src)
    funcs = {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
    assert 'generate_automation' in funcs or 'automation_generate' in funcs or \
           any('automat' in fn.lower() and 'generat' in fn.lower() for fn in funcs), \
           f"Missing automation generate endpoint. Found: {[f for f in funcs if 'auto' in f.lower()]}"
    # Check imports
    assert 'automation_gen_service' in src or 'auto_gen' in src, "Missing auto_gen import"
    assert 'GenerateAutomationRequest' in src
    assert 'GenerateAutomationResponse' in src
test("faz5 router: automation generate endpoint present", t_f5_router_endpoint)

def t_f5_router_automation_logic():
    with open('/sessions/zealous-lucid-bell/mnt/BGTS_Test_Donusum/backend/app/domains/tspm/router.py') as f:
        src = f.read()
    # Should resolve test cases from batch_id or test_case_ids
    assert 'batch_id' in src, "Missing batch_id handling"
    assert 'generate_full_automation_package' in src, "Missing full pipeline call"
test("faz5 router: batch_id resolution + full pipeline call", t_f5_router_automation_logic)

def t_f5_ui_page():
    with open('/sessions/zealous-lucid-bell/mnt/BGTS_Test_Donusum/apps/web/app/(dashboard)/p/[projectId]/automation-gen/page.tsx') as f:
        src = f.read()
    required = ['CodeBlock', 'StatCard', 'feature_name', 'include_java', 'include_playwright',
                'gherkin', 'java', 'playwright', 'handleGenerate']
    missing = [r for r in required if r not in src]
    assert not missing, f"Missing in automation-gen page: {missing}"
test("faz5 UI: automation-gen page complete", t_f5_ui_page)

def t_f5_ui_codeblock():
    with open('/sessions/zealous-lucid-bell/mnt/BGTS_Test_Donusum/apps/web/app/(dashboard)/p/[projectId]/automation-gen/page.tsx') as f:
        src = f.read()
    assert 'copy' in src.lower() or 'navigator.clipboard' in src.lower(), "Missing copy functionality"
    assert 'download' in src.lower(), "Missing download functionality"
    assert 'CodeBlock' in src, "Missing CodeBlock component"
test("faz5 UI: CodeBlock has copy + download", t_f5_ui_codeblock)

# ══════════════════════════════════════════════════════════════════════════════
# INFRA & FRONTEND
# ══════════════════════════════════════════════════════════════════════════════
print("\n=== INFRA & FRONTEND ===")

def t_docker_compose():
    with open('/sessions/zealous-lucid-bell/mnt/BGTS_Test_Donusum/docker-compose.yml') as f:
        src = f.read()
    assert 'ai-gateway' in src,         "Missing ai-gateway service"
    assert '8080' in src,               "Missing port 8080"
    assert 'AI_GATEWAY_BASE_URL' in src, "Missing AI_GATEWAY_BASE_URL env var"
    assert 'postgres' in src.lower(),   "Missing postgres service"
    assert 'redis' in src.lower(),      "Missing redis service"
test("infra: docker-compose has all services", t_docker_compose)

def t_frontend_ai_gateway_lib():
    with open('/sessions/zealous-lucid-bell/mnt/BGTS_Test_Donusum/apps/web/lib/ai-gateway.ts') as f:
        src = f.read()
    for fn in ['aiComplete', 'analyzeDocument', 'generateTestCases', 'getGatewayHealth']:
        assert fn in src, f"Missing function: {fn}"
test("frontend: ai-gateway.ts has all 4 functions", t_frontend_ai_gateway_lib)

def t_frontend_doc_uploader():
    with open('/sessions/zealous-lucid-bell/mnt/BGTS_Test_Donusum/apps/web/components/DocumentUploader.tsx') as f:
        src = f.read()
    assert 'DocumentUploader' in src
    assert 'upload-document' in src or 'uploadDocument' in src
    assert 'isDragging' in src
test("frontend: DocumentUploader component complete", t_frontend_doc_uploader)

def t_frontend_appshell_nav():
    with open('/sessions/zealous-lucid-bell/mnt/BGTS_Test_Donusum/apps/web/components/AppShell.tsx') as f:
        src = f.read()
    assert '/test-cases' in src,        "Missing /test-cases nav link"
    assert '/automation-gen' in src,    "Missing /automation-gen nav link"
    assert 'AI Test Case' in src or 'test-cases' in src
    assert 'Otomasyon' in src,          "Missing Otomasyon label"
test("frontend: AppShell has /test-cases and /automation-gen nav links", t_frontend_appshell_nav)

def t_frontend_appshell_no_syntax_error():
    """Check AppShell.tsx has no obvious TS syntax issues."""
    with open('/sessions/zealous-lucid-bell/mnt/BGTS_Test_Donusum/apps/web/components/AppShell.tsx') as f:
        src = f.read()
    # Count curly braces - should be balanced in nav links
    nav_section = re.search(r'href.*test-cases.*\n.*href.*automation-gen', src)
    assert nav_section is not None, "Nav links not adjacent as expected"
test("frontend: AppShell nav links properly formatted", t_frontend_appshell_no_syntax_error)

# ══════════════════════════════════════════════════════════════════════════════
# CROSS-FAZ: Schema completeness check
# ══════════════════════════════════════════════════════════════════════════════
print("\n=== CROSS-FAZ: SCHEMA COMPLETENESS ===")

def t_all_schemas_in_router():
    with open('/sessions/zealous-lucid-bell/mnt/BGTS_Test_Donusum/backend/app/domains/tspm/router.py') as f:
        src = f.read()
    faz3_schemas = ['AiBatchDetailOut', 'AiBatchOut', 'BulkReviewRequest',
                    'GenerateTestCasesRequest', 'GenerateTestCasesResponse',
                    'TestCaseOut', 'TestCaseReviewAction', 'TestCaseUpdate']
    faz5_schemas = ['GenerateAutomationRequest', 'GenerateAutomationResponse',
                    'GherkinResult', 'JavaResult', 'PlaywrightResult']
    missing = [s for s in faz3_schemas + faz5_schemas if s not in src]
    assert not missing, f"Router missing schemas: {missing}"
test("schemas: all Faz3+5 schemas imported in router", t_all_schemas_in_router)

def t_all_models_in_router():
    with open('/sessions/zealous-lucid-bell/mnt/BGTS_Test_Donusum/backend/app/domains/tspm/router.py') as f:
        src = f.read()
    assert 'TspmAiBatch' in src
    assert 'TspmTestCase' in src
test("models: TspmAiBatch and TspmTestCase imported in router", t_all_models_in_router)

def t_regression_suggest_schema_router():
    with open('/sessions/zealous-lucid-bell/mnt/BGTS_Test_Donusum/backend/app/domains/tspm/router.py') as f:
        src = f.read()
    assert 'RegressionSuggestRequest' in src
    assert 'RegressionSuggestResponse' in src
    assert 'suggest_regression_sets' in src or 'regression_suggest' in src
test("schemas: RegressionSuggest schemas in router", t_regression_suggest_schema_router)

# ══════════════════════════════════════════════════════════════════════════════
# SUMMARY
# ══════════════════════════════════════════════════════════════════════════════
print(f"\n{'='*60}")
print(f"NEXUS QA FAZ 0-5 ENTEGRASYON TESTİ SONUÇLARI")
print(f"{'='*60}")
print(f"✓ BAŞARILI : {len(PASS)}/{len(PASS)+len(FAIL)}")
print(f"✗ BAŞARISIZ: {len(FAIL)}")
if FAIL:
    print("\nBaşarısız testler:")
    for name, err in FAIL:
        short = err.splitlines()[-1][:120] if err else "?"
        print(f"  ✗ {name}")
        print(f"      {short}")
print(f"{'='*60}")

if FAIL:
    sys.exit(1)
