"""
tests/conftest.py — Test paketi köprüsü

- pytest-bdd step tanımlamaları steps/ klasöründen yüklenir
- Sentetik veri fixture'ları fixtures/ klasöründen yüklenir
- Auto-tagging: dosya yoluna göre marker ataması yapılır
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Auto-generated BDD files that reference feature files not present in this repo
collect_ignore = [
    str(Path(__file__).parent / "test_login_giris.py"),
    str(Path(__file__).parent / "test_Otomasyonlar_test.py"),
]

pytest_plugins = [
    "steps.conftest",
    "steps.common_steps",
    "tests.fixtures.conftest_synth",
]


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    for item in items:
        filepath = str(item.fspath)
        if "unit/" in filepath:
            item.add_marker(pytest.mark.unit)
        if "integration/" in filepath:
            item.add_marker(pytest.mark.integration)
        if "test_browser" in filepath:
            item.add_marker(pytest.mark.browser)
        if "test_ai" in filepath:
            item.add_marker(pytest.mark.ai)
            item.add_marker(pytest.mark.slow)
