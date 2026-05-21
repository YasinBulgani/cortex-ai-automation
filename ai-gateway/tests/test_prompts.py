from pathlib import Path

from app.core.models import TaskType
from app.core.prompt_registry import get_all_task_prompts
from app.core.prompts import get_system_prompt


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_all_prompts_include_global_guardrails():
    for task_type in TaskType:
        prompt = get_system_prompt(task_type)
        assert "Bilgin olmayan" in prompt
        assert "İstenen format dışına çıkma" in prompt


def test_document_prompt_requires_json_only():
    prompt = get_system_prompt(TaskType.ANALYZE_DOCUMENT)
    assert "Yalnızca tek bir geçerli JSON" in prompt
    assert '"modules"' in prompt


def test_gherkin_prompt_contains_dsl_and_needs_dsl_rule():
    prompt = get_system_prompt(TaskType.GENERATE_GHERKIN)
    assert "# language: tr" in prompt
    assert "@needs-dsl" in prompt
    assert "Yanıt yalnızca Gherkin" in prompt


def test_playwright_prompt_rejects_hard_waits():
    prompt = get_system_prompt(TaskType.GENERATE_PLAYWRIGHT)
    assert "waitForTimeout" in prompt
    assert "Stable locator önceliği" in prompt


def test_engine_prompt_assets_include_professional_quality_sections():
    prompt_expectations = {
        "prompt_center/engine/bdd_generator.md": [
            "Riskli bankacılık alanlarını atlama",
            "Çıktı Disiplini",
            "Gherkin feature dosyası",
        ],
        "prompt_center/engine/test_generator.md": [
            "Hard wait, sleep, rastgele retry",
            "sahte selector veya sahte route üretme",
            "Yalnızca tek bir fenced code block",
        ],
        "prompt_center/engine/self_healer.md": [
            "locator tamamen verilen tree'den türesin",
            "Dinamik index, nth-child",
            "Çıktı Disiplini",
        ],
        "prompt_center/engine/assertion_analyzer.md": [
            "Kodda veya senaryoda olmayan iş kuralını uydurma",
            "Önceliklendirme",
            "Bankacılık akışlarında",
        ],
        "prompt_center/engine/security_analyzer.md": [
            "Tarama çıktısında olmayan etkiyi",
            "Olasılık / Güven düzeyi",
            "Audit izi eksikliği",
        ],
    }

    for relative_path, expected_snippets in prompt_expectations.items():
        content = (REPO_ROOT / relative_path).read_text(encoding="utf-8")
        for snippet in expected_snippets:
            assert snippet in content


def test_prompt_center_manifest_contains_all_task_types():
    manifest_content = (REPO_ROOT / "prompt_center/manifest.json").read_text(encoding="utf-8")
    for task_type in TaskType:
        assert task_type.value in manifest_content


def test_registry_builds_prompts_for_all_task_types():
    prompts = get_all_task_prompts()
    assert set(prompts) == set(TaskType)
    assert "Yalnızca tek bir geçerli JSON" in prompts[TaskType.ANALYZE_DOCUMENT]
    assert "Yanıt yalnızca Gherkin" in prompts[TaskType.GENERATE_GHERKIN]
    assert "waitForTimeout" in prompts[TaskType.GENERATE_PLAYWRIGHT]


def test_rule_set_document_references_prompt_center():
    content = (REPO_ROOT / "docs/llm-rule-sets.md").read_text(encoding="utf-8")

    assert "prompt_center/manifest.json" in content
    assert "prompt_center/policies" in content
    assert "prompt_center/tasks" in content
    assert "prompt_center/engine" in content


def test_legacy_engine_prompt_docs_still_include_professional_sections():
    prompt_expectations = {
        "engine/prompts/bdd_generator_system.md": [
            "Riskli bankacılık alanlarını atlama",
            "Çıktı Disiplini",
        ],
        "engine/prompts/test_generator_system.md": [
            "Evrensel Kalite Kuralları",
            "Hard wait / sleep / kırılgan locator",
            "sahte selector veya sahte route üretme",
        ],
        "engine/prompts/self_healer_system.md": [
            "Evrensel Kalite Kuralları",
            "locator tamamen verilen tree'den türesin",
            "Çıktı Disiplini",
        ],
        "engine/prompts/assertion_analyzer_system.md": [
            "Evrensel Kalite Kuralları",
            "Önceliklendirme",
            "Bankacılık akışlarında",
        ],
        "engine/prompts/security_analyzer_system.md": [
            "Evrensel Kalite Kuralları",
            "Olasılık / Güven Düzeyi",
            "Raporlama Disiplini",
        ],
    }

    for relative_path, expected_snippets in prompt_expectations.items():
        content = (REPO_ROOT / relative_path).read_text(encoding="utf-8")
        for snippet in expected_snippets:
            assert snippet in content
