"""
Nexus QA — Faz 0-3 Kapsamlı Entegrasyon Testleri
"""
import sys, os, json, ast, re

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

# ── Faz 0: AI Gateway ──────────────────────────────────────────────────────────
print("\n=== FAZ 0: AI GATEWAY ===")

def t_gateway_main():
    with open('/sessions/zealous-lucid-bell/mnt/BGTS_Test_Donusum/ai-gateway/main.py') as f:
        src = f.read()
    assert 'on_event' not in src
    assert 'asynccontextmanager' in src
    assert 'lifespan=lifespan' in src
test("gateway main.py lifespan pattern", t_gateway_main)

def t_gateway_pytest_ini():
    with open('/sessions/zealous-lucid-bell/mnt/BGTS_Test_Donusum/ai-gateway/pytest.ini') as f:
        content = f.read()
    assert 'asyncio_mode = auto' in content
test("gateway pytest.ini with asyncio_mode=auto", t_gateway_pytest_ini)

def t_gateway_models():
    gw_path = '/sessions/zealous-lucid-bell/mnt/BGTS_Test_Donusum/ai-gateway'
    if gw_path not in sys.path:
        sys.path.insert(0, gw_path)
    from app.core.models import TaskType, ProviderName  # type: ignore
    assert 'generate_test_cases' in [t.value for t in TaskType]
    assert len(list(ProviderName)) >= 4
test("gateway models: TaskType & ProviderName", t_gateway_models)

def t_gateway_config():
    gw_path = '/sessions/zealous-lucid-bell/mnt/BGTS_Test_Donusum/ai-gateway'
    if gw_path not in sys.path:
        sys.path.insert(0, gw_path)
    from app.core.config import settings  # type: ignore
    assert settings.PORT == 8080
    assert 'groq' in settings.PROVIDER_ORDER
    assert settings.CHUNK_SIZE_TOKENS == 3000
test("gateway config: port & providers", t_gateway_config)

def t_gateway_prompts():
    gw_path = '/sessions/zealous-lucid-bell/mnt/BGTS_Test_Donusum/ai-gateway'
    if gw_path not in sys.path:
        sys.path.insert(0, gw_path)
    from app.core.prompts import PROMPTS  # type: ignore
    assert 'generate_test_cases' in PROMPTS
    assert len(PROMPTS) >= 5
test("gateway prompts: coverage", t_gateway_prompts)

# ── Backend tests use a fresh interpreter context via separate process ─────────
import subprocess, textwrap

def run_backend_test(code: str, test_name: str):
    full_code = textwrap.dedent(f"""
import sys, os
sys.path.insert(0, '/sessions/zealous-lucid-bell/mnt/BGTS_Test_Donusum/backend')
os.environ['DATABASE_URL'] = 'postgresql://test:test@localhost/test'
{code}
print("OK")
""")
    result = subprocess.run(
        ['python', '-c', full_code],
        capture_output=True, text=True, timeout=30
    )
    if result.returncode != 0 or 'OK' not in result.stdout:
        raise AssertionError(result.stderr.strip() or result.stdout.strip())

print("\n=== FAZ 1: DOCUMENT PARSING ===")

def t_doc_parser_import():
    run_backend_test("""
from app.domains.tspm.document_parser import parse_document, ParsedDocument
assert callable(parse_document)
""", "doc_parser_import")
test("document_parser: importable", t_doc_parser_import)

def t_doc_parser_txt():
    run_backend_test("""
from app.domains.tspm.document_parser import parse_document
content = b"# Test Sistemi\\n\\n## Login\\n\\nGiris modulu.\\n\\n## Rapor\\n\\nRapor modulu."
doc = parse_document(content, "test.txt", "text/plain")
assert doc.format == "txt", f"format={doc.format}"
assert "Login" in doc.full_text or "Giris" in doc.full_text
assert len(doc.sections) >= 1, f"sections={doc.sections}"
""", "doc_parser_txt")
test("document_parser: TXT parse with sections", t_doc_parser_txt)

def t_doc_chunking():
    run_backend_test("""
from app.domains.tspm.document_parser import parse_document
big = ("Sistem aciklamasi. " * 1000 + "\\n\\n")
doc = parse_document(big.encode(), "big.txt", "text/plain")
assert doc.word_count > 100
assert len(doc.chunks) >= 1
""", "doc_chunking")
test("document_parser: large file chunking", t_doc_chunking)

print("\n=== FAZ 2: BACKEND GATEWAY CLIENT ===")

def t_gw_client():
    run_backend_test("""
from app.domains.ai.gateway_client import (
    gateway_complete, gateway_analyze_document,
    gateway_generate_test_cases, gateway_is_available
)
assert callable(gateway_complete)
assert callable(gateway_is_available)
result = gateway_is_available()
assert isinstance(result, bool)
""", "gw_client")
test("gateway_client: functions importable + is_available bool", t_gw_client)

print("\n=== FAZ 3: TEST CASE GENERATION ===")

def t_f3_schemas():
    run_backend_test("""
from app.domains.tspm.schemas import (
    GenerateTestCasesRequest, GenerateTestCasesResponse,
    TestCaseOut, AiBatchOut, AiBatchDetailOut,
    BulkReviewRequest, TestCaseReviewAction, TestCaseUpdate
)
req = GenerateTestCasesRequest(
    analysis_text='Test sistemi gereksinimleri',
    source_name='req.pdf',
    modules=[{'module_name': 'Auth', 'risk_level': 'high', 'estimated_tests': 8}]
)
assert req.source_type == 'document'
bulk = BulkReviewRequest(ids=['id1','id2'], action='approve')
assert bulk.action == 'approve'
""", "f3_schemas")
test("faz3 schemas: all importable + validate", t_f3_schemas)

def t_f3_models():
    run_backend_test("""
from app.domains.tspm.models import TspmAiBatch, TspmTestCase
batch_cols = {c.key for c in TspmAiBatch.__table__.columns}
tc_cols = {c.key for c in TspmTestCase.__table__.columns}
required_b = {'id','project_id','status','total_generated','approved_count','rejected_count'}
required_t = {'id','project_id','batch_id','title','review_status','priority','risk_level','steps'}
assert required_b <= batch_cols, f'Missing: {required_b - batch_cols}'
assert required_t <= tc_cols, f'Missing: {required_t - tc_cols}'
""", "f3_models")
test("faz3 models: columns verified", t_f3_models)

def t_f3_service():
    run_backend_test("""
import json
from app.domains.tspm.test_case_service import (
    _parse_test_cases_json, _normalize_steps, _validate_enum, _build_prompt_for_modules
)
data = [{'title': 'TC1', 'priority': 'high'}, {'title': 'TC2'}]
assert _parse_test_cases_json(json.dumps(data)) == data
assert _parse_test_cases_json(json.dumps({'test_cases': data})) == data
fenced = '```json\\n' + json.dumps(data) + '\\n```'
assert _parse_test_cases_json(fenced) == data
steps = _normalize_steps([{'order': 1, 'action': 'Click', 'expected': 'Done'}])
assert steps[0]['action'] == 'Click'
steps2 = _normalize_steps(['Step one', 'Step two'])
assert len(steps2) == 2
assert _validate_enum('invalid', ['a','b'], 'b') == 'b'
assert _validate_enum('a', ['a','b'], 'b') == 'a'
prompt = _build_prompt_for_modules('Sistem', [{'module_name': 'Auth', 'risk_level': 'high', 'estimated_tests': 5}], 'Guvenlik')
assert 'Auth' in prompt and 'Guvenlik' in prompt
""", "f3_service")
test("faz3 service: parse/normalize/validate/prompt", t_f3_service)

def t_f3_scenario_conv():
    run_backend_test("""
import uuid
from app.domains.tspm.models import TspmTestCase
from app.domains.tspm.test_case_service import _test_case_to_scenario
tc = TspmTestCase(
    id=str(uuid.uuid4()), project_id=str(uuid.uuid4()),
    title='Session sona erdiginde yonlendirme',
    test_type='functional', priority='high', risk_level='high',
    preconditions=['Oturum acik olmali'],
    steps=[{'order':1,'action':'Bekle','expected':'Oturum biter'}],
    expected_result='Login sayfasina yonlendir',
    tags=['auth'], module_name='Auth', review_status='pending',
)
s = _test_case_to_scenario(tc)
assert s.title == tc.title
keywords = [x['keyword'] for x in s.steps]
assert 'Given' in keywords
assert 'When' in keywords or 'And' in keywords
assert 'Then' in keywords
""", "f3_scenario_conv")
test("faz3 service: TestCase → Scenario BDD steps", t_f3_scenario_conv)

def t_f3_router_endpoints():
    with open('/sessions/zealous-lucid-bell/mnt/BGTS_Test_Donusum/backend/app/domains/tspm/router.py') as f:
        src = f.read()
    tree = ast.parse(src)
    funcs = {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
    required = ['generate_test_cases','list_batches','get_batch','delete_batch',
                'list_test_cases','get_test_case','update_test_case',
                'review_test_case','bulk_review_test_cases','delete_test_case']
    for fn in required:
        assert fn in funcs, f"Missing: {fn}"
test("faz3 router: all 10 endpoints present", t_f3_router_endpoints)

def t_f3_ui_page():
    with open('/sessions/zealous-lucid-bell/mnt/BGTS_Test_Donusum/apps/web/app/(dashboard)/p/[projectId]/test-cases/page.tsx') as f:
        src = f.read()
    assert 'TestCaseCard' in src
    assert 'EditModal' in src
    assert 'bulk-review' in src
    assert 'handleApprove' in src
    assert 'handleReject' in src
    assert 'handleBulkAction' in src
    assert 'filterStatus' in src
    assert 'generate' in src
test("faz3 UI: test-cases page complete", t_f3_ui_page)

def t_f3_nav():
    with open('/sessions/zealous-lucid-bell/mnt/BGTS_Test_Donusum/apps/web/components/AppShell.tsx') as f:
        src = f.read()
    assert '/test-cases' in src
test("faz3 nav: /test-cases in AppShell", t_f3_nav)

print("\n=== FAZ 0-2: INFRA & FRONTEND ===")

def t_docker():
    with open('/sessions/zealous-lucid-bell/mnt/BGTS_Test_Donusum/docker-compose.yml') as f:
        src = f.read()
    assert 'ai-gateway' in src
    assert '8080' in src
    assert 'AI_GATEWAY_BASE_URL' in src
test("infra: docker-compose ai-gateway service", t_docker)

def t_ai_gw_ts():
    with open('/sessions/zealous-lucid-bell/mnt/BGTS_Test_Donusum/apps/web/lib/ai-gateway.ts') as f:
        src = f.read()
    for fn in ['aiComplete', 'analyzeDocument', 'generateTestCases', 'getGatewayHealth']:
        assert fn in src, f"Missing {fn}"
test("frontend: ai-gateway.ts functions", t_ai_gw_ts)

def t_doc_uploader():
    with open('/sessions/zealous-lucid-bell/mnt/BGTS_Test_Donusum/apps/web/components/DocumentUploader.tsx') as f:
        src = f.read()
    assert 'DocumentUploader' in src
    assert 'upload-document' in src
    assert 'isDragging' in src
test("frontend: DocumentUploader component", t_doc_uploader)

# ── Gateway pytest ─────────────────────────────────────────────────────────────
print("\n=== FAZ 0: GATEWAY PYTEST (6 testler) ===")
result = subprocess.run(
    ['python', '-m', 'pytest', 'tests/', '-v', '--tb=short'],
    capture_output=True, text=True, timeout=60,
    cwd='/tmp/nexusqa-test'
)
if '6 passed' in result.stdout:
    print("  ✓ AI Gateway: 6/6 test geçti")
    PASS.append("AI Gateway pytest: 6/6")
else:
    print(f"  ✗ Gateway tests: {result.stdout[-400:]}")
    FAIL.append(("AI Gateway pytest", result.stdout[-200:]))

# ── Summary ────────────────────────────────────────────────────────────────────
print(f"\n{'='*55}")
print(f"NEXUS QA FAZ 0-3 TEST SONUÇLARI")
print(f"{'='*55}")
print(f"✓ BAŞARILI: {len(PASS)}")
print(f"✗ BAŞARISIZ: {len(FAIL)}")
if FAIL:
    print("\nBAŞARISIZ TESTLER:")
    for name, err in FAIL:
        print(f"  ✗ {name}")
        print(f"    {err[:120]}")
else:
    print("\n🎉 Tüm testler başarılı! Faz 0-3 hazır.")
print('='*55)
sys.exit(1 if FAIL else 0)
