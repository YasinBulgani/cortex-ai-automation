"""Privacy service guard tests."""

from __future__ import annotations

from app.domains.privacy import service


def test_purge_artifacts_only_deletes_under_artifacts_dir(tmp_path, monkeypatch):
    artifacts_root = tmp_path / "artifacts"
    artifacts_root.mkdir()
    inside = artifacts_root / "run" / "report.json"
    inside.parent.mkdir()
    inside.write_text("{}", encoding="utf-8")
    outside = tmp_path / "outside.txt"
    outside.write_text("keep", encoding="utf-8")

    monkeypatch.setattr(service.settings, "artifacts_dir", str(artifacts_root))

    deleted, skipped = service._purge_artifact_files([str(inside), str(outside)])

    assert deleted == [str(inside)]
    assert skipped == [str(outside)]
    assert not inside.exists()
    assert outside.exists()
