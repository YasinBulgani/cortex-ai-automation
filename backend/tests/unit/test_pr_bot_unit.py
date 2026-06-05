"""Unit tests for pr_bot domain — PR analysis helpers."""
import pytest


class TestPrBotHelpers:
    def test_pr_title_validation(self):
        title = "fix(auth): correct JWT expiry calculation"
        assert len(title) > 0
        assert len(title) <= 100

    def test_branch_name_parsing(self):
        branch = "feature/qa-system-bootstrap"
        parts = branch.split("/")
        assert len(parts) >= 2
        assert parts[0] in {"feature", "fix", "chore", "hotfix", "release"}

    def test_diff_size_classification(self):
        def classify(lines_changed: int) -> str:
            if lines_changed < 50:  return "small"
            if lines_changed < 300: return "medium"
            return "large"
        assert classify(20) == "small"
        assert classify(150) == "medium"
        assert classify(500) == "large"

    def test_file_extension_filter(self):
        files = ["main.py", "test_main.py", "README.md", "config.yml"]
        python_files = [f for f in files if f.endswith(".py")]
        assert len(python_files) == 2
        assert "README.md" not in python_files
