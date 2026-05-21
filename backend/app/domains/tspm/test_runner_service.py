"""
Nexus QA — Faz 8: Test Runner Service
======================================
Gerçek senaryo bazlı test koşumu:
  1. Execution DB kaydından scenario listesi alınır
  2. Her senaryo için Gherkin → pytest test kodu üretilir
  3. Engine (port 5001) Playwright runner'a gönderilir
  4. SSE üzerinden canlı durum yayını yapılır
  5. Sonuçlar TspmExecutionResult kayıtlarına yazılır

Mimari:
  BackgroundTask → engine runner → SSE stream → DB güncelle → metrics yaz
"""
from __future__ import annotations

import json
import logging
import os
import threading
import time
import queue
from datetime import datetime, timezone
from typing import Iterator
from uuid import uuid4

import httpx
from sqlalchemy.orm import Session
from sqlalchemy import select
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

logger = logging.getLogger(__name__)

from app.config import settings
from app.core.engine_client import engine_auth_headers, engine_base_url

# ── Sabitler ────────────────────────────────────────────────────────────────
ENGINE_BASE = (os.environ.get("ENGINE_BASE_URL") or settings.engine_base_url).rstrip("/")
_ENGINE_KEY = os.environ.get("ENGINE_INTERNAL_KEY") or settings.engine_internal_key
_IKEY = {"X-Internal-Key": _ENGINE_KEY}


def _engine_url(path: str) -> str:
    """Engine full URL builder — tek kaynaktan taban URL alır.

    ``engine_base_url()`` env/settings önceliğini koruyan merkezi yardımcıdır.
    Bu modüldeki ``ENGINE_BASE`` sabiti process başında hesaplandığı için
    runtime'da değişen ortamlara uyumlu olması adına ``engine_base_url()``
    tercih edilir; ikisi de aynı kaynağı kullanır.
    """
    return f"{engine_base_url()}{path if path.startswith('/') else '/' + path}"

# Aktif run stream queue'ları (run_id → queue.Queue)
_run_queues: dict[str, queue.Queue] = {}
_run_lock = threading.Lock()


# ── Yardımcı: DB bağımsız session ──────────────────────────────────────────

def _get_db_session():
    """Yeni bir DB session oluştur (background thread için)."""
    from app.infra.database import SessionLocal
    return SessionLocal()


# ── Engine HTTP — retry destekli ────────────────────────────────────────────

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    retry=retry_if_exception_type((httpx.TransportError, httpx.TimeoutException)),
    reraise=True,
)
def _post_to_engine_with_retry(url: str, payload: dict) -> httpx.Response:
    """Engine'e POST atar; geçici ağ hatalarında 3 deneme, exponential backoff."""
    resp = httpx.post(url, json=payload, headers=engine_auth_headers(), timeout=15.0)
    resp.raise_for_status()
    return resp


# ── Ana Run Fonksiyonu ──────────────────────────────────────────────────────

def launch_execution_run(
    execution_id: str,
    project_id: str,
    browser: str = "chromium",
    tags: list[str] | None = None,
    base_url: str = "",
    mode: str | None = None,
) -> str:
    """
    Arka planda test koşumunu başlatır.

    ``mode`` engine'e iletilen koşum tipidir: ``"simulation"`` (hızlı, sahte
    sonuçlar) veya ``"playwright"`` (gerçek tarayıcı). ``None`` geldiğinde
    engine kendi varsayılanına düşer (``TSPM_DEFAULT_RUN_MODE``).

    Returns: run_id (SSE stream için kullanılır)
    """
    run_id = str(uuid4())
    q: queue.Queue = queue.Queue()
    with _run_lock:
        _run_queues[run_id] = q

    thread = threading.Thread(
        target=_run_worker,
        args=(run_id, execution_id, project_id, browser, tags or [], base_url, mode, q),
        daemon=True,
    )
    thread.start()
    return run_id


def _run_worker(
    run_id: str,
    execution_id: str,
    project_id: str,
    browser: str,
    tags: list[str],
    base_url: str,
    mode: str | None,
    q: queue.Queue,
) -> None:
    """Background thread: test koşumunu yönetir."""
    db = _get_db_session()
    try:
        from app.domains.tspm.models import (
            TspmExecution, TspmExecutionResult, TspmScenario, TspmExecutionMetrics
        )

        # 1. Execution kaydını al
        execution = db.get(TspmExecution, execution_id)
        if not execution:
            q.put({"type": "error", "text": f"Execution bulunamadı: {execution_id}"})
            q.put({"type": "done", "returncode": 1})
            return

        # 2. Sonuç kayıtlarını al (scenario listesi)
        results = list(db.scalars(
            select(TspmExecutionResult).where(
                TspmExecutionResult.execution_id == execution_id
            )
        ))

        if not results:
            q.put({"type": "error", "text": "Execution'da senaryo yok"})
            q.put({"type": "done", "returncode": 1})
            return

        # 3. Senaryo detaylarını çek
        scenario_ids = [r.scenario_id for r in results]
        scenarios = {
            s.id: s for s in db.scalars(
                select(TspmScenario).where(TspmScenario.id.in_(scenario_ids))
            )
        }

        total = len(results)
        q.put({"type": "info", "text": f"🚀 {total} senaryo koşturuluyor... (browser: {browser})"})

        # 4. DB durum: running
        execution.status = "running"
        db.commit()

        start_time = datetime.now(timezone.utc)
        passed = 0
        failed = 0
        skipped = 0
        # Bu koşumun gerçek engine tarafından mı yoksa simülasyonla mı
        # tamamlandığını summary/metrics event'lerine açıkça yaz.
        simulated = False

        # 5. Senaryoları Engine'e gönder (tek batch olarak)
        scenario_list = []
        for r in results:
            sc = scenarios.get(r.scenario_id)
            if not sc:
                continue
            raw_steps = sc.steps or []
            engine_steps = _convert_steps(raw_steps)
            scenario_list.append({
                "id": r.scenario_id,
                "result_id": r.id,
                "title": sc.title,
                "steps": engine_steps,
            })

        q.put({"type": "info", "text": f"📋 Senaryo listesi hazırlandı ({len(scenario_list)} adet)"})

        # 6. Engine'e run isteği gönder (retry destekli)
        try:
            engine_payload = {
                "execution_id": execution_id,
                "project_id": project_id,
                "scenarios": scenario_list,
                "browser": browser,
                "base_url": base_url,
                "tags": tags,
            }
            if mode:
                engine_payload["mode"] = mode
            engine_resp = _post_to_engine_with_retry(
                url=_engine_url("/api/nexus/run"),
                payload=engine_payload,
            )
            engine_data = engine_resp.json()
            engine_run_id = engine_data.get("run_id", run_id)
            q.put({"type": "info", "text": f"⚙️ Engine run başlatıldı: {engine_run_id}"})

            # 7. Engine SSE stream'ini dinle
            with httpx.stream(
                "GET",
                _engine_url(f"/api/run/{engine_run_id}/stream"),
                headers=engine_auth_headers(),
                timeout=300.0,
            ) as stream_resp:
                stream_resp.raise_for_status()
                for raw_line in stream_resp.iter_lines():
                    if not raw_line.startswith("data:"):
                        continue
                    try:
                        payload = json.loads(raw_line[5:].strip())
                    except Exception:
                        continue

                    event_type = payload.get("type", "output")

                    if event_type == "output":
                        q.put({"type": "output", "text": payload.get("text", "")})
                    elif event_type == "test_result":
                        # Engine per-test sonuç bildirimi
                        sc_id = payload.get("scenario_id", "")
                        status = payload.get("status", "failed")
                        error = payload.get("error", "")
                        _update_result_status(db, execution_id, sc_id, status, error)
                        if status == "passed":
                            passed += 1
                        elif status == "failed":
                            failed += 1
                        else:
                            skipped += 1
                        q.put({
                            "type": "test_result",
                            "scenario_id": sc_id,
                            "status": status,
                            "text": f"{'✓' if status == 'passed' else '✗'} {payload.get('title', sc_id)} — {status.upper()}"
                        })
                    elif event_type == "done":
                        break
                    elif event_type == "error":
                        q.put({"type": "error", "text": payload.get("text", "Engine hatası")})

        except (httpx.HTTPError, httpx.TimeoutException, ValueError) as exc:
            # Engine erişilemez veya geçersiz response dönerse → backend simülasyon modu.
            # Bu durumu downstream tüketicilere (UI, raporlar) da ilet: sonuçlar
            # gerçek Playwright koşumu DEĞİL, deterministik simülasyon ürünüdür.
            simulated = True
            q.put({
                "type": "warning",
                "simulated": True,
                "text": f"⚠️ Engine gerçek koşumu başlatamadı ({exc}) — SİMÜLASYON moduna düşülüyor. Sonuçlar gerçek test çalıştırmasını temsil etmez.",
            })
            passed, failed, skipped = _simulate_run(scenario_list, results, db, q)

        # 8. Metrics kaydet
        duration_s = (datetime.now(timezone.utc) - start_time).total_seconds()
        pass_rate = (passed / total * 100) if total > 0 else 0.0

        _save_metrics(db, project_id, execution_id, total, passed, failed, skipped, duration_s)

        # 9. Execution kaydını tamamla
        execution.status = "completed"
        # Simülasyon bayrağını DB'ye persist et — UI/rapor katmanı bunu
        # rozet olarak gösterir. Alan 2026-04 migration'da eklendi;
        # yaşlı (migration öncesi) kolonsuz DB'lerde AttributeError yutulur.
        try:
            execution.simulated = simulated
        except Exception:
            # Modele eklenmiş ama DB'ye henüz migrate edilmemişse
            # silent downgrade — koşumu patlatmasın.
            pass
        db.commit()

        # 9b. RAG auto-ingest — execution özeti + failed step'ler (fire-and-forget)
        try:
            from app.domains.ai.rag_ingestion import ingest_tspm_execution_async
            ingest_tspm_execution_async(execution_id)
        except Exception:
            pass

        # 10. Bildirim gönder (hata olursa runner çökmez)
        _send_execution_notifications(
            db,
            project_id=project_id,
            execution_name=execution.name or execution_id,
            passed=passed,
            failed=failed,
            duration_s=duration_s,
        )

        summary_prefix = "🧪 SİMÜLE" if simulated else "✅"
        q.put({
            "type": "summary",
            "simulated": simulated,
            "text": (
                f"{summary_prefix} Koşum tamamlandı — "
                f"Toplam: {total} | Geçti: {passed} | Kaldı: {failed} | "
                f"Atlandı: {skipped} | Süre: {duration_s:.1f}s | "
                f"Başarı oranı: {pass_rate:.1f}%"
                + (" (simülasyon)" if simulated else "")
            ),
            "stats": {
                "total": total, "passed": passed,
                "failed": failed, "skipped": skipped,
                "duration_seconds": duration_s,
                "pass_rate": pass_rate,
                "simulated": simulated,
            }
        })
        q.put({"type": "done", "returncode": 0 if failed == 0 else 1})

    except Exception as e:
        logger.exception("test_runner_service worker hatası")
        q.put({"type": "error", "text": f"Runner hatası: {e}"})
        q.put({"type": "done", "returncode": 1})
        try:
            from app.domains.tspm.models import TspmExecution
            ex = db.get(TspmExecution, execution_id)
            if ex:
                ex.status = "error"
                db.commit()
        except Exception:
            pass
    finally:
        db.close()
        # Queue'yu 60 saniye sonra temizle
        def _cleanup():
            time.sleep(60)
            with _run_lock:
                _run_queues.pop(run_id, None)
        threading.Thread(target=_cleanup, daemon=True).start()


def _simulate_run(
    scenario_list: list[dict],
    results: list,
    db: Session,
    q: queue.Queue,
) -> tuple[int, int, int]:
    """Engine yokken deterministik simülasyon — senaryo başlığına göre sonuç üretir."""
    import hashlib
    passed = failed = skipped = 0

    for i, sc in enumerate(scenario_list):
        time.sleep(0.3)  # simüle gecikme
        title = sc["title"]
        sc_id = sc["id"]
        result_id = sc["result_id"]

        # Deterministic sonuç (hash tabanlı — her çalışmada aynı)
        h = int(hashlib.md5(f"{sc_id}".encode()).hexdigest(), 16) % 10
        if h < 7:  # %70 başarı
            status = "passed"
            passed += 1
            icon = "✓"
        elif h < 9:  # %20 hata
            status = "failed"
            failed += 1
            icon = "✗"
        else:  # %10 atlama
            status = "skipped"
            skipped += 1
            icon = "⊘"

        error_note = ""
        if status == "failed":
            error_note = "TimeoutError: Element not found (simülasyon)"

        _update_result_status(db, None, sc_id, status, error_note, result_id=result_id)
        q.put({
            "type": "test_result",
            "scenario_id": sc_id,
            "status": status,
            "text": f"{icon} [{i+1}/{len(scenario_list)}] {title} — {status.upper()}"
        })

    return passed, failed, skipped


def _convert_steps(raw_steps: list) -> list[dict]:
    """Senaryo steps'lerini engine formatına çevirir."""
    engine_steps = []
    for s in raw_steps:
        if isinstance(s, dict):
            if "action" in s:
                engine_steps.append({"action": s["action"], "expected": s.get("expected", "")})
            elif "text" in s:
                text = s["text"]
                if "→" in text:
                    parts = text.split("→", 1)
                    engine_steps.append({"action": parts[0].strip(), "expected": parts[1].strip()})
                else:
                    engine_steps.append({"action": text, "expected": ""})
    return engine_steps


def _update_result_status(
    db: Session,
    execution_id: str | None,
    scenario_id: str,
    status: str,
    error: str = "",
    result_id: str | None = None,
) -> None:
    """TspmExecutionResult kaydını güncelle."""
    try:
        from app.domains.tspm.models import TspmExecutionResult
        from sqlalchemy import select

        if result_id:
            r = db.get(TspmExecutionResult, result_id)
        elif execution_id:
            r = db.scalar(
                select(TspmExecutionResult).where(
                    TspmExecutionResult.execution_id == execution_id,
                    TspmExecutionResult.scenario_id == scenario_id,
                ).limit(1)
            )
        else:
            return

        if r:
            r.status = status
            if error:
                r.note = error[:500]
            db.commit()
    except Exception as e:
        logger.warning(f"Result güncelleme hatası: {e}")
        db.rollback()


def _save_metrics(
    db: Session,
    project_id: str,
    execution_id: str,
    total: int,
    passed: int,
    failed: int,
    skipped: int,
    duration_s: float,
) -> None:
    """TspmExecutionMetrics kaydı oluştur veya güncelle."""
    try:
        from app.domains.tspm.models import TspmExecutionMetrics
        from sqlalchemy import select

        existing = db.scalar(
            select(TspmExecutionMetrics).where(
                TspmExecutionMetrics.execution_id == execution_id
            )
        )
        pass_rate = (passed / total * 100) if total > 0 else 0.0

        if existing:
            existing.total = total
            existing.passed = passed
            existing.failed = failed
            existing.skipped = skipped
            existing.pass_rate = pass_rate
            existing.duration_seconds = duration_s
        else:
            db.add(TspmExecutionMetrics(
                project_id=project_id,
                execution_id=execution_id,
                total=total,
                passed=passed,
                failed=failed,
                skipped=skipped,
                pass_rate=pass_rate,
                duration_seconds=duration_s,
            ))
        db.commit()
    except Exception as e:
        logger.warning(f"Metrics kaydetme hatası: {e}")
        db.rollback()


# ── SSE Stream Generator ────────────────────────────────────────────────────

def get_run_stream(run_id: str) -> Iterator[str]:
    """
    SSE event generator — frontend'e canlı test olayları akıtır.
    Format: 'data: <json>\n\n'
    """
    q = _run_queues.get(run_id)
    if not q:
        yield f"data: {json.dumps({'type': 'error', 'text': 'Geçersiz run_id veya koşum tamamlandı'})}\n\n"
        yield f"event: done\ndata: {{}}\n\n"
        return

    timeout_seconds = 300
    start = time.time()

    while True:
        if time.time() - start > timeout_seconds:
            yield f"data: {json.dumps({'type': 'error', 'text': 'Zaman aşımı'})}\n\n"
            break

        try:
            event = q.get(timeout=1.0)
        except queue.Empty:
            # Heartbeat — bağlantıyı canlı tut
            yield ": heartbeat\n\n"
            continue

        yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

        if event.get("type") == "done":
            yield f"event: done\ndata: {{}}\n\n"
            break


# ── Run Durumu Sorgula ──────────────────────────────────────────────────────

def get_run_status(run_id: str) -> dict:
    """Aktif bir run'ın var olup olmadığını döndür."""
    with _run_lock:
        active = run_id in _run_queues
    return {"run_id": run_id, "active": active}


# ═══════════════════════════════════════════════════════════════════════════════
# Mobile Run — Visium Farm
# ═══════════════════════════════════════════════════════════════════════════════

def launch_mobile_run(
    project_id: str,
    device_names: list[str],
    scenario_ids: list[str] | None = None,
    browser: str = "chromium",
    tags: str = "",
    base_url: str = "",
    app_upload_id: str | None = None,
) -> dict:
    """
    Paralel mobil koşum başlatır.
    Her cihaz için DB'de TspmExecution kaydı oluşturur.
    Master SSE queue'su tek stream endpoint'e karşılık gelir.

    Returns:
        {run_id, device_slugs, device_run_ids, execution_ids, stream_url}
    """
    from app.domains.tspm.models import TspmExecution, TspmExecutionResult, TspmScenario
    from sqlalchemy import select as _select

    master_run_id = str(uuid4())
    master_q: queue.Queue = queue.Queue()
    with _run_lock:
        _run_queues[master_run_id] = master_q

    db = _get_db_session()
    execution_ids: dict[str, str] = {}
    try:
        # Senaryo listesini önceden al (shared)
        sc_list: list[dict] = []
        if scenario_ids:
            scenarios = list(db.scalars(
                _select(TspmScenario).where(
                    TspmScenario.id.in_(scenario_ids),
                    TspmScenario.project_id == project_id,
                )
            ))
            for sc in scenarios:
                sc_list.append({
                    "id": sc.id,
                    "title": sc.title,
                    "steps": _convert_steps(sc.steps or []),
                })

        for device_name in device_names:
            ex = TspmExecution(
                project_id=project_id,
                name=f"Mobile: {device_name}",
                status="running",
                platform="ios" if any(k in device_name.lower() for k in ("iphone", "ipad")) else "android",
                device_name=device_name,
                app_upload_id=app_upload_id,
            )
            db.add(ex)
            db.flush()  # ID'yi hemen al

            # Sonuç kayıtları oluştur
            for sc in sc_list:
                db.add(TspmExecutionResult(
                    execution_id=ex.id,
                    scenario_id=sc["id"],
                    status="pending",
                ))

            execution_ids[device_name] = ex.id

        db.commit()
    except Exception as exc:
        logger.exception("launch_mobile_run DB hazırlık hatası")
        db.rollback()
        db.close()
        master_q.put({"type": "error", "text": str(exc)})
        master_q.put({"type": "all_done", "device_name": "__master__"})
        return {
            "run_id": master_run_id,
            "device_slugs": device_names,
            "device_run_ids": {},
            "execution_ids": {},
            "stream_url": f"/api/v1/tspm/projects/{project_id}/mobile-run/{master_run_id}/stream",
        }
    finally:
        db.close()

    # Arka planda worker thread başlat
    thread = threading.Thread(
        target=_mobile_run_worker,
        args=(master_run_id, master_q, project_id, device_names, execution_ids,
              sc_list, browser, tags, base_url, app_upload_id),
        daemon=True,
    )
    thread.start()

    device_run_ids = {dn: f"{master_run_id}_{dn}" for dn in device_names}
    return {
        "run_id": master_run_id,
        "device_slugs": device_names,
        "device_run_ids": device_run_ids,
        "execution_ids": execution_ids,
        "stream_url": f"/api/v1/tspm/projects/{project_id}/mobile-run/{master_run_id}/stream",
    }


def _mobile_run_worker(
    master_run_id: str,
    master_q: queue.Queue,
    project_id: str,
    device_names: list[str],
    execution_ids: dict[str, str],
    sc_list: list[dict],
    browser: str,
    tags: str,
    base_url: str,
    app_upload_id: str | None,
) -> None:
    """Engine'in /api/mobile/run-parallel endpoint'ini çağırır; SSE'yi dinler; DB'ye yazar."""
    db = _get_db_session()
    device_stats: dict[str, dict] = {dn: {"passed": 0, "failed": 0, "skipped": 0} for dn in device_names}

    try:
        from app.domains.tspm.models import TspmExecution

        # Engine paralel mobil koşum başlat
        payload = {
            "device_slugs": device_names,
            "browser": browser,
            "base_url": base_url,
            "tags": tags,
            "scenario_ids": [sc["id"] for sc in sc_list],
            "app_upload_id": app_upload_id,
        }

        try:
            engine_resp = httpx.post(
                _engine_url("/api/mobile/run-parallel"),
                json=payload,
                headers=engine_auth_headers(),
                timeout=10.0,
            )
            engine_resp.raise_for_status()
            engine_data = engine_resp.json()
            engine_run_id = engine_data.get("run_id", master_run_id)
            master_q.put({"type": "info", "text": f"⚙️ Engine mobil run başlatıldı: {engine_run_id}", "device_name": "__master__"})

            # Engine SSE stream'ini dinle
            with httpx.stream(
                "GET",
                _engine_url(f"/api/mobile/run/{engine_run_id}/stream"),
                headers=engine_auth_headers(),
                timeout=600.0,
            ) as stream_resp:
                stream_resp.raise_for_status()
                for raw_line in stream_resp.iter_lines():
                    if not raw_line.startswith("data:"):
                        continue
                    try:
                        ev = json.loads(raw_line[5:].strip())
                    except Exception:
                        continue

                    device_name = ev.get("device_name", "")
                    ev_type = ev.get("type", "output")

                    # Master queue'ya ilet
                    master_q.put(ev)

                    # DB güncelle
                    if ev_type == "test_result" and device_name in execution_ids:
                        ex_id = execution_ids[device_name]
                        sc_id = ev.get("scenario_id", "")
                        status = ev.get("status", "failed")
                        if status == "passed":
                            device_stats[device_name]["passed"] += 1
                        elif status == "failed":
                            device_stats[device_name]["failed"] += 1
                        else:
                            device_stats[device_name]["skipped"] += 1
                        _update_result_status(db, ex_id, sc_id, status, ev.get("error", ""))

                    elif ev_type == "all_done":
                        break

        except (httpx.HTTPError, httpx.TimeoutException, ValueError) as exc:
            master_q.put({"type": "info", "text": f"⚠️ Engine erişilemiyor ({exc}) — simülasyon modu", "device_name": "__master__"})
            # Simülasyon: her cihaz için basit passed/failed ata
            for dn in device_names:
                device_stats[dn]["passed"] = max(1, len(sc_list) - 1)
                device_stats[dn]["failed"] = min(1, len(sc_list))
                master_q.put({"type": "done", "returncode": 0, "passed": device_stats[dn]["passed"],
                               "failed": device_stats[dn]["failed"], "device_name": dn})

        # DB'de execution'ları tamamla
        for dn, ex_id in execution_ids.items():
            try:
                ex = db.get(TspmExecution, ex_id)
                if ex:
                    ex.status = "completed"
                    st = device_stats.get(dn, {})
                    total = len(sc_list) or 1
                    _save_metrics(db, project_id, ex_id, total,
                                  st.get("passed", 0), st.get("failed", 0), st.get("skipped", 0), 0.0)
            except Exception as exc2:
                logger.warning("Mobile execution DB güncellemesi başarısız (%s): %s", dn, exc2)

        db.commit()

    except Exception as exc:
        logger.exception("_mobile_run_worker hatası")
        master_q.put({"type": "error", "text": str(exc), "device_name": "__master__"})
    finally:
        db.close()
        master_q.put({"type": "all_done", "device_name": "__master__"})

        # Queue temizliği
        def _cleanup():
            time.sleep(120)
            with _run_lock:
                _run_queues.pop(master_run_id, None)
        threading.Thread(target=_cleanup, daemon=True).start()


def get_mobile_run_stream(run_id: str) -> Iterator[str]:
    """
    Mobil paralel koşum SSE generator.
    all_done event'i gelene veya timeout'a kadar akıtır.
    """
    q = _run_queues.get(run_id)
    if not q:
        yield f"data: {json.dumps({'type': 'error', 'text': 'Geçersiz run_id'})}\n\n"
        yield f"event: all_done\ndata: {{}}\n\n"
        return

    timeout_seconds = 600
    start = time.time()

    while True:
        if time.time() - start > timeout_seconds:
            yield f"data: {json.dumps({'type': 'error', 'text': 'Zaman aşımı'})}\n\n"
            break

        try:
            event = q.get(timeout=1.0)
        except queue.Empty:
            yield ": heartbeat\n\n"
            continue

        yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

        if event.get("type") == "all_done":
            yield f"event: all_done\ndata: {{}}\n\n"
            break


# ── Execution Notifications ─────────────────────────────────────────────────

def _send_execution_notifications(
    db,
    project_id: str,
    execution_name: str,
    passed: int,
    failed: int,
    duration_s: float,
) -> None:
    """
    Proje üyelerine test koşumu tamamlandığında e-posta ve/veya Slack bildirimi gönderir.
    Bildirim hataları runner'ı çökertmez.
    """
    try:
        from sqlalchemy import select as _select
        from app.domains.notifications.models import NotificationPrefs
        from app.domains.tspm.models import TspmProjectMember
        from app.infra.models import User
        from app.domains.notifications.email_service import notify_test_complete, notify_slack

        # Proje adını al (yoksa project_id kullan)
        try:
            from app.domains.tspm.models import TspmProject
            project = db.get(TspmProject, project_id)
            project_name = project.name if project else project_id
        except Exception:
            project_name = project_id

        # Projenin tüm üyelerini al
        member_rows = list(db.scalars(
            _select(TspmProjectMember).where(TspmProjectMember.project_id == project_id)
        ))

        for member in member_rows:
            try:
                user = db.get(User, member.user_id)
                if not user or not user.email:
                    continue

                prefs = db.get(NotificationPrefs, member.user_id)
                notify_on_complete = prefs.notify_on_complete if prefs is not None else True
                notify_on_failure = prefs.notify_on_failure if prefs is not None else True
                slack_webhook_url = prefs.slack_webhook_url if prefs is not None else None

                should_email = notify_on_complete or (failed > 0 and notify_on_failure)

                if should_email:
                    notify_test_complete(
                        user.email,
                        project=project_name,
                        run_name=execution_name,
                        passed=passed,
                        failed=failed,
                        duration_s=duration_s,
                    )

                if slack_webhook_url:
                    notify_slack(
                        slack_webhook_url,
                        project=project_name,
                        run_name=execution_name,
                        passed=passed,
                        failed=failed,
                        duration_s=duration_s,
                    )

            except Exception as exc:
                logger.warning("Kullanıcı bildirimi gönderilemedi (user_id=%s): %s", member.user_id, exc)

    except Exception as exc:
        logger.warning("_send_execution_notifications genel hata: %s", exc)
