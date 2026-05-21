"""
API Testing Business Logic Service
===================================

Spec parsing, AI test generation, execution orchestration.
"""

import json
import logging
import time
from typing import Any, Dict, List, Optional, Tuple, Union
from uuid import uuid4

from sqlalchemy.orm import Session

from app.domains.api_testing.models import (
    ApiChain,
    ApiEndpoint,
    ApiEnvironment,
    ApiExecutionDetail,
    ApiSpec,
    ApiTestCase,
)
from app.domains.api_testing.spec_parser import parse_spec, SpecAnalysis
from app.domains.api_testing.environment import merge_variables, resolve_dict
from app.domains.api_testing.request_executor import execute_request, ExecutionResult
from app.domains.api_testing.feedback_loop import (
    enrich_generation_prompt,
    learn_from_execution,
)

logger = logging.getLogger(__name__)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SPEC OPERATIONS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def import_spec(
    db: Session,
    project_id: str,
    content: Union[str, dict],
    *,
    name: Optional[str] = None,
    source_url: Optional[str] = None,
    source_file: Optional[str] = None,
) -> Tuple[ApiSpec, SpecAnalysis]:
    """
    OpenAPI/Swagger spec import et, parse et, endpoint'leri DB'ye kaydet.

    Returns: (ApiSpec model, SpecAnalysis dataclass)
    """
    # 1. Parse + Analiz
    analysis = parse_spec(content, resolve=True)

    if analysis.errors:
        raise ValueError(f"Spec parse hatalari: {'; '.join(analysis.errors)}")

    # 2. Spec kaydini olustur
    spec_name = name or analysis.title or "Untitled API"
    raw_content = content if isinstance(content, dict) else json.loads(content) if content.strip().startswith("{") else {}

    spec = ApiSpec(
        id=str(uuid4()),
        project_id=project_id,
        name=spec_name,
        version=analysis.version,
        spec_format=analysis.spec_format,
        spec_content=raw_content if isinstance(raw_content, dict) else {},
        source_url=source_url,
        source_file=source_file,
        endpoint_count=analysis.endpoint_count,
        schema_count=analysis.schema_count,
    )
    db.add(spec)
    db.flush()

    # 3. Endpoint'leri kaydet
    for ep_info in analysis.endpoints:
        endpoint = ApiEndpoint(
            id=str(uuid4()),
            spec_id=spec.id,
            method=ep_info.method,
            path=ep_info.path,
            operation_id=ep_info.operation_id,
            summary=ep_info.summary,
            description=ep_info.description,
            tags=ep_info.tags,
            parameters=ep_info.parameters,
            request_body_schema=ep_info.request_body_schema,
            response_schemas=ep_info.response_schemas,
            security_requirements=ep_info.security_requirements,
            auth_required=ep_info.auth_required,
            risk_level=ep_info.risk_level,
            has_pii=ep_info.has_pii,
            has_financial=ep_info.has_financial,
            compliance_tags=ep_info.compliance_tags,
            depends_on=ep_info.depends_on,
        )
        db.add(endpoint)

    db.commit()
    db.refresh(spec)

    logger.info(
        "Spec import: %s — %d endpoint, %d schema, %d critical, %d PII",
        spec_name, analysis.endpoint_count, analysis.schema_count,
        analysis.critical_count, analysis.pii_endpoint_count,
    )

    return spec, analysis


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# AI TEST GENERATION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def generate_tests_with_ai(
    db: Session,
    project_id: str,
    *,
    spec_id: Optional[str] = None,
    endpoint_ids: Optional[List[str]] = None,
    mode: str = "test_generation",
    regulations: Optional[List[str]] = None,
    test_types: Optional[List[str]] = None,
    max_tests_per_endpoint: int = 8,
    owasp_focus: Optional[List[str]] = None,
    additional_context: Optional[str] = None,
) -> Dict[str, Any]:
    """
    AI ile test case / guvenlik testi / chain uret.

    Returns: {mode, generated_count, test_cases, warnings, ai_model, duration_ms}
    """
    from app.domains.agents.banking_team.service_test_agent import ServiceTestAgent

    t_start = time.time()
    warnings: List[str] = []

    # 1. Endpoint'leri topla
    endpoints: List[dict] = []
    if endpoint_ids:
        eps = db.query(ApiEndpoint).filter(ApiEndpoint.id.in_(endpoint_ids)).all()
        for ep in eps:
            endpoints.append({
                "method": ep.method,
                "path": ep.path,
                "operation_id": ep.operation_id,
                "summary": ep.summary,
                "description": ep.description,
                "parameters": ep.parameters,
                "request_body_schema": ep.request_body_schema,
                "response_schemas": ep.response_schemas,
                "risk_level": ep.risk_level,
                "has_pii": ep.has_pii,
                "has_financial": ep.has_financial,
                "compliance_tags": ep.compliance_tags,
            })
    elif spec_id:
        eps = db.query(ApiEndpoint).filter(ApiEndpoint.spec_id == spec_id).all()
        for ep in eps:
            endpoints.append({
                "method": ep.method,
                "path": ep.path,
                "operation_id": ep.operation_id,
                "summary": ep.summary,
                "parameters": ep.parameters,
                "request_body_schema": ep.request_body_schema,
                "response_schemas": ep.response_schemas,
                "risk_level": ep.risk_level,
                "has_pii": ep.has_pii,
                "has_financial": ep.has_financial,
                "compliance_tags": ep.compliance_tags,
            })

    if not endpoints:
        return {"mode": mode, "generated_count": 0, "test_cases": [],
                "warnings": ["Endpoint bulunamadi"], "duration_ms": 0}

    # 2. Feedback loop'tan ogrenme baglamini al
    enrichment = {}  # type: Dict[str, Any]
    try:
        enrichment = enrich_generation_prompt(
            project_id=project_id,
            endpoints=endpoints,
            mode=mode,
            db=db,
        )
    except Exception as exc:
        logger.warning("Feedback loop enrichment hatasi (devam ediliyor): %s", exc)
        warnings.append(f"Ogrenme baglami alinamadi: {exc}")

    # 3. AI agent'i calistir
    agent = ServiceTestAgent()
    agent_ctx = {
        "mode": mode,
        "endpoints": endpoints,
        "regulations": regulations or ["BDDK", "KVKK"],
        "test_types": test_types or ["positive", "negative", "boundary", "security", "compliance"],
        "max_tests_per_endpoint": max_tests_per_endpoint,
        "owasp_focus": owasp_focus or [],
        "additional_context": additional_context or "",
    }

    # Enrichment verisini agent context'ine ekle
    if enrichment.get("learnings"):
        agent_ctx["learnings"] = enrichment["learnings"]
    if enrichment.get("failure_patterns"):
        failure_text = "\n".join(f"- {p}" for p in enrichment["failure_patterns"])
        existing_ctx = agent_ctx.get("additional_context", "")
        if existing_ctx:
            agent_ctx["additional_context"] = (
                existing_ctx + "\n\n## BILINEN HATA PATERNLERI\n" + failure_text
            )
        else:
            agent_ctx["additional_context"] = "## BILINEN HATA PATERNLERI\n" + failure_text
    if enrichment.get("previously_generated_count", 0) > 0:
        count = enrichment["previously_generated_count"]
        existing_ctx = agent_ctx.get("additional_context", "")
        note = f"\nNOT: Bu endpoint'ler icin zaten {count} adet test case mevcut. Tekrar uretmekten kacinin."
        agent_ctx["additional_context"] = (existing_ctx + note) if existing_ctx else note

    result = agent.safe_run(agent_ctx)

    if not result.success:
        warnings.append(f"AI uretim hatasi: {result.error}")
        return {"mode": mode, "generated_count": 0, "test_cases": [],
                "warnings": warnings, "duration_ms": int((time.time() - t_start) * 1000)}

    # 3. Sonuclari DB'ye kaydet
    data = result.data or {}
    test_cases_raw = data.get("test_cases", [])
    security_tests_raw = data.get("security_tests", [])
    chains_raw = data.get("chains", [])

    saved_cases: List[ApiTestCase] = []

    # Test case'leri kaydet
    all_raw = test_cases_raw + security_tests_raw
    for tc_raw in all_raw:
        try:
            req = tc_raw.get("request", {})
            tc = ApiTestCase(
                id=str(uuid4()),
                project_id=project_id,
                title=tc_raw.get("title", "Untitled"),
                description=tc_raw.get("description"),
                test_type=tc_raw.get("test_type", tc_raw.get("owasp", "positive")),
                priority=tc_raw.get("priority", "P2"),
                owasp_category=tc_raw.get("owasp_category", tc_raw.get("owasp")),
                regulation=tc_raw.get("regulation"),
                cwe_id=tc_raw.get("cwe"),
                request_method=req.get("method", tc_raw.get("endpoint", {}).get("method", "GET")),
                request_path=req.get("path", tc_raw.get("endpoint", {}).get("path", "/")),
                request_headers=req.get("headers", {}),
                request_params=req.get("params", {}),
                request_body=req.get("body"),
                setup_chain=tc_raw.get("setup_chain"),
                assertions=tc_raw.get("assertions", []),
                ai_generated=True,
                ai_model=agent.model,
                ai_confidence=tc_raw.get("confidence"),
                ai_reasoning=tc_raw.get("ai_reasoning", tc_raw.get("attack_scenario")),
            )

            # Endpoint ile eslestir
            if endpoint_ids and len(endpoint_ids) == 1:
                tc.endpoint_id = endpoint_ids[0]

            db.add(tc)
            saved_cases.append(tc)
        except Exception as exc:
            warnings.append(f"Test case kayit hatasi: {exc}")

    # Chain'leri kaydet
    saved_chains: List[dict] = []
    for chain_raw in chains_raw:
        try:
            steps = chain_raw.get("steps", [])
            nodes = []
            edges = []

            for i, step in enumerate(steps):
                node_id = f"n{i+1}"
                nodes.append({
                    "id": node_id,
                    "type": "request",
                    "position": {"x": i * 300, "y": 0},
                    "data": {
                        "label": step.get("label", f"Step {i+1}"),
                        "method": step.get("endpoint", {}).get("method", "GET"),
                        "path": step.get("endpoint", {}).get("path", "/"),
                    },
                })
                if i > 0:
                    prev_step = steps[i - 1]
                    edges.append({
                        "id": f"e{i}",
                        "source": f"n{i}",
                        "target": node_id,
                        "data": {
                            "mappings": [
                                {"from_path": ext.get("json_path", ""), "to_var": ext.get("name", "")}
                                for ext in prev_step.get("extract", [])
                            ],
                        },
                    })

            chain = ApiChain(
                id=str(uuid4()),
                project_id=project_id,
                name=chain_raw.get("name", "Untitled Chain"),
                description=chain_raw.get("description"),
                nodes=nodes,
                edges=edges,
                ai_generated=True,
                ai_reasoning=chain_raw.get("description"),
            )
            db.add(chain)
            saved_chains.append({"id": chain.id, "name": chain.name})
        except Exception as exc:
            warnings.append(f"Chain kayit hatasi: {exc}")

    db.commit()

    duration_ms = int((time.time() - t_start) * 1000)

    return {
        "mode": mode,
        "generated_count": len(saved_cases),
        "test_case_ids": [tc.id for tc in saved_cases],
        "chains": saved_chains,
        "security_findings": data.get("risk_matrix"),
        "warnings": warnings,
        "ai_model": agent.model,
        "duration_ms": duration_ms,
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# EXECUTION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def execute_test_cases(
    db: Session,
    project_id: str,
    test_case_ids: List[str],
    *,
    environment_id: Optional[str] = None,
    stop_on_failure: bool = False,
) -> Dict[str, Any]:
    """
    Test case'leri calistir ve sonuclari kaydet.

    Returns: {run_id, total, passed, failed, errors, duration_ms, results[]}
    """
    from app.domains.tspm.models import TspmApiTestRun

    # Environment degiskenlerini al
    env_vars: Dict[str, str] = {}
    if environment_id:
        env = db.query(ApiEnvironment).get(environment_id)
        if env:
            env_vars = env.variables or {}

    # Test case'leri yukle
    test_cases = db.query(ApiTestCase).filter(
        ApiTestCase.id.in_(test_case_ids),
        ApiTestCase.project_id == project_id,
    ).all()

    if not test_cases:
        return {"run_id": "", "total": 0, "passed": 0, "failed": 0,
                "errors": 0, "duration_ms": 0, "results": []}

    # Run kaydini olustur
    run = TspmApiTestRun(
        id=str(uuid4()),
        collection_id=test_cases[0].collection_id,
        status="running",
        results=[],
    )
    db.add(run)
    db.flush()

    t_start = time.time()
    results: List[dict] = []
    chain_vars = dict(env_vars)
    passed_count = 0
    failed_count = 0
    error_count = 0

    for tc in test_cases:
        # URL olustur
        base_url = env_vars.get("base_url", "http://127.0.0.1:8000")
        url = f"{base_url.rstrip('/')}{tc.request_path}"

        # Execute
        exec_result = await execute_request(
            method=tc.request_method,
            url=url,
            headers=tc.request_headers,
            params=tc.request_params,
            body=tc.request_body,
            variables=chain_vars,
            assertions=tc.assertions,
            timeout=30.0,
        )

        # Chain variables guncelle
        if exec_result.extracted_variables:
            chain_vars.update(exec_result.extracted_variables)

        # Sonuc durumu belirle
        if exec_result.error:
            status = "error"
            error_count += 1
        elif exec_result.assertion_report and exec_result.assertion_report.all_passed:
            status = "passed"
            passed_count += 1
        elif exec_result.assertion_report:
            status = "failed"
            failed_count += 1
        else:
            # Assertion yok — sadece HTTP basarisi kontrol et
            status = "passed" if exec_result.status_code and exec_result.status_code < 400 else "failed"
            if status == "passed":
                passed_count += 1
            else:
                failed_count += 1

        # Execution detail kaydet
        detail = ApiExecutionDetail(
            id=str(uuid4()),
            run_id=run.id,
            test_case_id=tc.id,
            actual_method=exec_result.method,
            actual_url=exec_result.url,
            actual_headers=exec_result.headers_sent,
            actual_body=exec_result.body_sent if isinstance(exec_result.body_sent, dict) else None,
            status_code=exec_result.status_code,
            response_headers=exec_result.response_headers,
            response_body=exec_result.response_body[:100_000] if exec_result.response_body else None,
            response_size_bytes=exec_result.response_size_bytes,
            total_ms=exec_result.timing.total_ms,
            assertion_results=[r.to_dict() for r in (exec_result.assertion_report.results if exec_result.assertion_report else [])],
            passed=(status == "passed"),
            error_message=exec_result.error,
            schema_valid=exec_result.schema_valid,
            schema_errors=exec_result.schema_errors,
            extracted_variables=exec_result.extracted_variables,
            execution_order=len(results),
        )
        db.add(detail)

        # Test case durumunu guncelle
        tc.last_run_status = status
        tc.last_run_at = detail.executed_at
        tc.last_run_duration_ms = exec_result.timing.total_ms
        tc.run_count += 1
        if status == "passed":
            tc.pass_count += 1
        else:
            tc.fail_count += 1

        results.append({
            "test_case_id": tc.id,
            "title": tc.title,
            "method": exec_result.method,
            "url": exec_result.url,
            "status_code": exec_result.status_code,
            "status": status,
            "total_ms": round(exec_result.timing.total_ms, 2),
            "assertion_results": detail.assertion_results,
            "error": exec_result.error,
        })

        # Stop on failure
        if stop_on_failure and status in ("failed", "error"):
            break

    # Run kaydini tamamla
    total_ms = (time.time() - t_start) * 1000
    run.status = "completed"
    run.results = results
    db.commit()

    # Feedback loop — calisma sonuclarindan ogen (fire-and-forget)
    try:
        learn_from_execution(db, run.id, project_id)
    except Exception as exc:
        logger.warning("Feedback loop learn_from_execution hatasi (yok sayildi): %s", exc)

    return {
        "run_id": run.id,
        "total": len(results),
        "passed": passed_count,
        "failed": failed_count,
        "errors": error_count,
        "duration_ms": round(total_ms, 2),
        "results": results,
    }
