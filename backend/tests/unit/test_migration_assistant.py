"""Regression tests for migration assistant — MIGRATION_REQUIRED fix.

2026-05-24: sessiz '// TODO' yerine runtime'da patlayan stub üretilmesi.
"""
from __future__ import annotations

import pytest

from app.domains.migration.assistant import migrate_selenium_java


SAMPLE_JAVA = '''
@Given("kullanıcı ana sayfadadır")
public void kullanici_ana_sayfadadir() { }

@When("kullanıcı login butonuna tıklar")
public void kullanici_login_butonuna_tiklar() { }

@When("bilinmeyen_super_ozel_action_xyz yapılır")
public void bilinmeyen_action() { }
'''


def test_migrate_java_no_silent_todo():
    result = migrate_selenium_java(SAMPLE_JAVA)
    assert "// TODO: manual migration" not in result.output_code
    for step in result.migrated:
        assert "TODO: manual migration" not in step.translated_code


def test_migrate_java_unknown_has_migration_required():
    result = migrate_selenium_java(SAMPLE_JAVA)
    unknown = [s for s in result.migrated if "MIGRATION_REQUIRED" in s.translated_code]
    assert len(unknown) >= 1, "bilinmeyen action MIGRATION_REQUIRED içermelidir"


def test_migrate_java_known_patterns_work():
    result = migrate_selenium_java(SAMPLE_JAVA)
    assert result.steps_total > 0
    known = [s for s in result.migrated if "MIGRATION_REQUIRED" not in s.translated_code]
    assert len(known) > 0, "En az bir bilinen pattern dönüştürülmeli"


def test_migrate_java_unhandled_tracked():
    result = migrate_selenium_java(SAMPLE_JAVA)
    assert result.steps_unhandled >= 1
