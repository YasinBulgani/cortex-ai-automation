from services.prompt_loader import get_engine_prompt, get_task_prompt


def test_engine_prompt_loader_returns_centralized_prompts():
    self_healer = get_engine_prompt("self_healer")
    security = get_engine_prompt("security_analyzer")

    assert "locator tamamen verilen tree'den türesin" in self_healer
    assert "Tarama çıktısında olmayan etkiyi" in security


def test_task_prompt_loader_can_read_gateway_tasks():
    playwright = get_task_prompt("generate_playwright")
    gherkin = get_task_prompt("generate_gherkin")

    assert "waitForTimeout" in playwright
    assert "@needs-dsl" in gherkin
