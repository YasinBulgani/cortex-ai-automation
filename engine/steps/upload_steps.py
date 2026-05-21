"""
steps/upload_steps.py — Dosya Yukleme BDD Adimlari
(NexusQA FileUploadHttpHelper pattern'inin Playwright adaptasyonu)

Desteklenen adimlar:
  When kullanici "{key}" alanina "{file}" dosyasini yukler
  When kullanici "{key}" alanindaki dosyayi temizler
"""
from pathlib import Path

from pytest_bdd import when, parsers

from config.settings import settings
from core.context import GlobalContext
from core.actions import Actions

_TEST_FILES_DIR = settings.BASE_DIR / "data" / "testfiles"


def _resolve_file(filename: str) -> Path:
    """Dosya adini test dosyalari dizininde arar."""
    path = _TEST_FILES_DIR / filename
    if path.exists():
        return path
    direct = Path(filename)
    if direct.exists():
        return direct
    raise FileNotFoundError(f"Test dosyasi bulunamadi: {filename} (aranan: {path})")


@when(parsers.parse('kullanici "{key}" alanina "{file}" dosyasini yukler'))
def step_upload_file(page, key, file):
    key = GlobalContext.render(key)
    file = GlobalContext.render(file)
    actions = Actions(page)
    actions.upload_file(key, _resolve_file(file))


@when(parsers.parse('kullanici "{key}" alanindaki dosyayi temizler'))
def step_clear_upload(page, key):
    key = GlobalContext.render(key)
    Actions(page).clear_upload(key)
