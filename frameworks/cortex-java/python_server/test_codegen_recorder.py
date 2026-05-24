"""
Regression tests for codegen_recorder.CodegenJob serialization.

Why this file exists
--------------------
On 2026-05-24 a Flask 500 surfaced from /api/cortex/codegen/start:

    TypeError: cannot pickle '_thread.lock' object
        File "codegen_recorder.py", line 46, in to_dict
            d = asdict(self)

Root cause: `asdict()` deepcopies every dataclass field BEFORE the caller
gets a chance to strip non-serializable ones. `CodegenJob._proc` holds a
live `subprocess.Popen`, which contains a `threading.Lock` — deepcopy
explodes. The `d.pop("_proc")` that followed was dead code reached only
on success.

These tests pin the contract:
  * to_dict() must succeed even when _proc is a live Popen.
  * The returned dict must be JSON-serializable (this is what Flask does
    via `jsonify`).
  * The "_proc" key must not appear in the output.

Runs with stdlib only (unittest) — no pytest dep needed in this server.
Invoke with: python3 -m unittest test_codegen_recorder
"""
import json
import subprocess
import sys
import unittest

from codegen_recorder import CodegenJob


def _make_live_popen() -> subprocess.Popen:
    """Spawn a short-lived idle subprocess to attach as ._proc."""
    return subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(30)"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


class CodegenJobToDictTest(unittest.TestCase):
    def setUp(self) -> None:
        self.proc = _make_live_popen()
        self.addCleanup(self._kill_proc)

    def _kill_proc(self) -> None:
        try:
            self.proc.terminate()
            self.proc.wait(timeout=2)
        except Exception:
            try:
                self.proc.kill()
            except Exception:
                pass
        for pipe in (self.proc.stdout, self.proc.stderr, self.proc.stdin):
            if pipe is not None:
                try:
                    pipe.close()
                except Exception:
                    pass

    def test_to_dict_does_not_raise_with_live_popen(self) -> None:
        """The 2026-05-24 regression: asdict() blew up on _proc's internal lock."""
        job = CodegenJob(
            id="test123",
            url="https://example.com",
            output_file="/tmp/test123.js",
            pid=self.proc.pid,
            status="running",
            _proc=self.proc,
        )
        # Must not raise TypeError: cannot pickle '_thread.lock'
        d = job.to_dict()
        self.assertIsInstance(d, dict)

    def test_to_dict_is_json_serializable(self) -> None:
        """Flask's jsonify() calls json.dumps — that's the path that failed."""
        job = CodegenJob(
            id="test123",
            url="https://example.com",
            output_file="/tmp/test123.js",
            pid=self.proc.pid,
            status="running",
            _proc=self.proc,
        )
        # Should not raise; verifies the dict has no non-JSON values either.
        payload = json.dumps(job.to_dict())
        self.assertIn('"id": "test123"', payload)

    def test_to_dict_omits_proc(self) -> None:
        """_proc is an internal handle — must never leak to API consumers."""
        job = CodegenJob(
            id="test123",
            url="https://example.com",
            output_file="/tmp/test123.js",
            _proc=self.proc,
        )
        d = job.to_dict()
        self.assertNotIn("_proc", d)

    def test_to_dict_preserves_public_fields(self) -> None:
        """Stop-the-bleed test: make sure we didn't accidentally drop a field
        that the frontend reads (CortexScenarioAuthor.tsx uses .id, .pid, .status)."""
        job = CodegenJob(
            id="abc",
            url="https://example.com",
            output_file="/tmp/abc.js",
            pid=42,
            status="running",
            error=None,
        )
        d = job.to_dict()
        for k in ("id", "url", "output_file", "pid", "status",
                  "started_at", "stopped_at", "error"):
            self.assertIn(k, d, f"public field '{k}' missing from to_dict()")
        self.assertEqual(d["id"], "abc")
        self.assertEqual(d["pid"], 42)
        self.assertEqual(d["status"], "running")


if __name__ == "__main__":
    unittest.main()
