"""Test Runner — Sandbox'ta Playwright koştur + JUnit parse."""
from __future__ import annotations

import asyncio
import logging
import os
import shutil
from urllib.parse import urlparse
import uuid
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import Any

from ..schemas.run import FailureContext, RunResult, TestStatus

logger = logging.getLogger(__name__)


async def run_playwright_tests(
    *,
    test_files: list[str | Path],
    run_id: str | None = None,
    base_url: str | None = None,
    environment: str = "sandbox",
    browser: str = "chromium",
    timeout_seconds: int = 600,
    use_docker: bool = False,
    sandbox_required: bool = False,
    docker_image: str = "mcr.microsoft.com/playwright:v1.49-jammy",
    docker_cpu_limit: str = "4",
    docker_memory_limit: str = "4g",
    network_allowlist: list[str] | None = None,
    workdir: str | Path = ".",
) -> RunResult:
    run_id = run_id or str(uuid.uuid4())
    start = datetime.utcnow()

    if use_docker:
        if not _has_docker():
            if sandbox_required:
                return _mock_result(run_id, start, reason="docker_required_not_available")
            logger.warning("Docker yok; Playwright local runner'a düşüyor")
        elif base_url and not _is_host_allowed(base_url, network_allowlist or []):
            return _mock_result(run_id, start, reason="base_url_not_allowlisted")
        else:
            return await _run_in_docker(
                test_files=test_files,
                run_id=run_id,
                base_url=base_url,
                environment=environment,
                browser=browser,
                timeout_seconds=timeout_seconds,
                docker_image=docker_image,
                docker_cpu_limit=docker_cpu_limit,
                docker_memory_limit=docker_memory_limit,
                workdir=workdir,
                started_at=start,
            )

    if not _has_npx():
        return _mock_result(run_id, start, reason="npx_not_available")

    workdir_path = Path(workdir).resolve()
    existing = [
        _resolve_test_file(f, workdir_path)
        for f in test_files
        if _resolve_test_file(f, workdir_path).exists()
    ]
    if not existing:
        return _mock_result(run_id, start, reason="no_test_files")

    junit_path = workdir_path / f".twai-junit-{run_id[:8]}.xml"
    env = os.environ.copy()
    if base_url:
        env["BASE_URL"] = base_url
    env["PLAYWRIGHT_JUNIT_OUTPUT_NAME"] = str(junit_path)

    cmd = [
        "npx", "playwright", "test", "--reporter=junit",
        *[str(f) for f in existing],
    ]

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd, cwd=str(workdir_path), env=env,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=timeout_seconds
            )
        except asyncio.TimeoutError:
            proc.kill()
            return _timeout_result(run_id, start, timeout_seconds)
    except FileNotFoundError:
        return _mock_result(run_id, start, reason="npx_not_found")
    except Exception as exc:
        logger.exception("Playwright çalıştırılamadı: %s", exc)
        return _mock_result(run_id, start, reason=f"exception: {exc}")

    result = parse_junit_xml(
        junit_path=junit_path, run_id=run_id, started_at=start,
        environment=environment, browser=browser,
    )
    try:
        junit_path.unlink(missing_ok=True)
    except Exception:
        pass
    return result


async def _run_in_docker(
    *,
    test_files: list[str | Path],
    run_id: str,
    base_url: str | None,
    environment: str,
    browser: str,
    timeout_seconds: int,
    docker_image: str,
    docker_cpu_limit: str,
    docker_memory_limit: str,
    workdir: str | Path,
    started_at: datetime,
) -> RunResult:
    workdir_path = Path(workdir).resolve()
    existing = [
        _resolve_test_file(f, workdir_path)
        for f in test_files
        if _resolve_test_file(f, workdir_path).exists()
    ]
    if not existing:
        return _mock_result(run_id, started_at, reason="no_test_files")

    container_files: list[str] = []
    for file_path in existing:
        container_path = _container_path_for(file_path, workdir_path)
        if container_path is None:
            logger.warning("Test file sandbox workdir disinda: %s", file_path)
            return _mock_result(run_id, started_at, reason="test_file_outside_workdir")
        container_files.append(container_path)

    junit_name = f".twai-junit-{run_id[:8]}.xml"
    junit_path = workdir_path / junit_name
    docker_env = ["-e", f"PLAYWRIGHT_JUNIT_OUTPUT_NAME=/work/{junit_name}"]
    if base_url:
        docker_env += ["-e", f"BASE_URL={base_url}"]

    network_args = ["--network", "bridge"] if base_url else ["--network", "none"]
    cmd = [
        "docker", "run", "--rm",
        "--cpus", docker_cpu_limit,
        "--memory", docker_memory_limit,
        *network_args,
        "-v", f"{workdir_path}:/work:rw",
        "-w", "/work",
        *docker_env,
        docker_image,
        "npx", "playwright", "test", "--reporter=junit",
        *container_files,
    ]

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            await asyncio.wait_for(proc.communicate(), timeout=timeout_seconds)
        except asyncio.TimeoutError:
            proc.kill()
            return _timeout_result(run_id, started_at, timeout_seconds)
    except FileNotFoundError:
        return _mock_result(run_id, started_at, reason="docker_not_found")
    except Exception as exc:
        logger.exception("Docker sandbox çalıştırılamadı: %s", exc)
        return _mock_result(run_id, started_at, reason=f"docker_exception: {exc}")

    result = parse_junit_xml(
        junit_path=junit_path, run_id=run_id, started_at=started_at,
        environment=environment, browser=browser,
    )
    try:
        junit_path.unlink(missing_ok=True)
    except Exception:
        pass
    return result


def parse_junit_xml(
    *,
    junit_path: Path,
    run_id: str,
    started_at: datetime,
    environment: str = "sandbox",
    browser: str = "chromium",
) -> RunResult:
    if not junit_path.exists():
        return RunResult(
            run_id=run_id, status=TestStatus.BROKEN,
            started_at=started_at, finished_at=datetime.utcnow(),
            environment=environment, browser=browser,
        )

    try:
        tree = ET.parse(junit_path)  # nosec B314 - JUnit output file, not user-supplied XML
        root = tree.getroot()
    except Exception:
        return RunResult(
            run_id=run_id, status=TestStatus.BROKEN,
            started_at=started_at, finished_at=datetime.utcnow(),
            environment=environment, browser=browser,
        )

    passed = 0
    failed = 0
    skipped = 0
    duration = 0.0
    failure_contexts: list[FailureContext] = []

    suites = [root] if root.tag == "testsuite" else root.findall("testsuite")

    for suite in suites:
        suite_duration = float(suite.get("time", "0") or 0)
        duration += suite_duration
        for case in suite.findall("testcase"):
            name = case.get("name", "")
            classname = case.get("classname", "")
            test_id = f"{classname}::{name}"

            failure = case.find("failure")
            error = case.find("error")
            skip = case.find("skipped")

            if failure is not None or error is not None:
                failed += 1
                fc = FailureContext(
                    test_id=test_id,
                    test_name=name,
                    spec_file=classname,
                    status=TestStatus.FAILED,
                    error_type=(
                        (failure.get("type") if failure is not None else None)
                        or (error.get("type") if error is not None else "")
                        or "AssertionError"
                    ),
                    error_message=(
                        (failure.text if failure is not None else "")
                        or (error.text if error is not None else "")
                        or ""
                    )[:1000],
                    stack_trace=(
                        (failure.text if failure is not None else "")
                        or (error.text if error is not None else "")
                        or ""
                    ),
                )
                failure_contexts.append(fc)
            elif skip is not None:
                skipped += 1
            else:
                passed += 1

    total = passed + failed + skipped
    if total == 0:
        status = TestStatus.BROKEN
    elif failed > 0:
        status = TestStatus.FAILED
    elif passed > 0:
        status = TestStatus.PASSED
    else:
        status = TestStatus.SKIPPED

    return RunResult(
        run_id=run_id,
        status=status,
        passed_count=passed,
        failed_count=failed,
        skipped_count=skipped,
        total_count=total,
        duration_seconds=duration,
        started_at=started_at,
        finished_at=datetime.utcnow(),
        failure_contexts=failure_contexts,
        environment=environment,
        browser=browser,
    )


def _has_npx() -> bool:
    return shutil.which("npx") is not None


def _has_docker() -> bool:
    return shutil.which("docker") is not None


def _container_path_for(file_path: str | Path, workdir: Path) -> str | None:
    path = Path(file_path).resolve()
    try:
        rel = path.relative_to(workdir)
    except ValueError:
        return None
    return f"/work/{rel.as_posix()}"


def _resolve_test_file(file_path: str | Path, workdir: Path) -> Path:
    path = Path(file_path)
    return path if path.is_absolute() else workdir / path


def _is_host_allowed(url: str, allowlist: list[str]) -> bool:
    if not allowlist:
        return False
    host = (urlparse(url).hostname or "").lower()
    if not host:
        return False
    for pattern in allowlist:
        pat = pattern.strip().lower()
        if not pat:
            continue
        if pat == host:
            return True
        if pat.startswith("*.") and host.endswith(pat[1:]):
            return True
    return False


def _mock_result(run_id: str, started: datetime, *, reason: str) -> RunResult:
    return RunResult(
        run_id=run_id, status=TestStatus.PENDING, total_count=0,
        started_at=started, finished_at=datetime.utcnow(),
    )


def _timeout_result(run_id: str, started: datetime, timeout_s: int) -> RunResult:
    return RunResult(
        run_id=run_id, status=TestStatus.TIMEOUT, total_count=0,
        duration_seconds=float(timeout_s),
        started_at=started, finished_at=datetime.utcnow(),
    )
