"""
Fine-Tune Data Export — yuksek kaliteli prompt/response pair'lerini JSONL'e yaz.

Kaynaklar (oncelik sirasina gore):
    1. ``llm_judge_runs.overall >= 9`` + success trace'leri  -> kesinlikle iyi
    2. ``few_shot_examples.quality_score = 10`` (seed + verified) -> referans set

OpenAI fine-tuning format:
    {"messages": [
        {"role": "system", "content": "..."},
        {"role": "user", "content": "..."},
        {"role": "assistant", "content": "..."}
    ]}
    Tek cagri = tek satir JSONL.

Anthropic format benzer (messages API). Ollama LoRA için ayni format uyumlu.

Gelecek kullanim:
    3 ay sonra 500+ kaliteli pair birikince gpt-4o-mini'yi bu datayla fine-tune
    ederek PREMIUM kalitesini MINI fiyatina cekmek mumkun.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


_DEFAULT_OUTPUT_DIR = Path("./data/finetune")


@dataclass
class ExportResult:
    path: str
    total_pairs: int
    from_judge: int
    from_few_shot: int
    task_types: list[str]


def export_finetune_jsonl(
    *,
    output_dir: Optional[str] = None,
    min_judge_score: float = 9.0,
    task_types: Optional[list[str]] = None,
    include_few_shot: bool = True,
    days: int = 90,
) -> ExportResult:
    """
    Fine-tune için JSONL dosyasi üret.

    Args:
        output_dir:        Cikti dizini (default ./data/finetune)
        min_judge_score:   Judge overall >= bu deger olan trace'ler dahil
        task_types:        Filtrelenecek task tipleri (None = hepsi)
        include_few_shot:  few_shot_examples'tan verified olanlari dahil et
        days:              Son N gun (judge + trace)

    Returns:
        ExportResult(path, total_pairs, from_judge, from_few_shot, task_types)
    """
    out_dir = Path(output_dir) if output_dir else _DEFAULT_OUTPUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    from datetime import datetime, timezone
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_path = out_dir / f"finetune_{ts}.jsonl"

    pairs_judge = _collect_from_judge(min_judge_score, task_types, days)
    pairs_fewshot = _collect_from_few_shot(task_types) if include_few_shot else []

    all_pairs = pairs_judge + pairs_fewshot

    with out_path.open("w", encoding="utf-8") as f:
        for pair in all_pairs:
            f.write(json.dumps(pair, ensure_ascii=False) + "\n")

    task_set: set[str] = set()
    for p in all_pairs:
        for m in p.get("messages", []):
            if m.get("role") == "system":
                # task_type metadata'ya yerlestirmiyoruz — message icerigi + context yeterli
                pass
    # task_type'lari payload'dan cikar
    task_set = {
        p.get("_task_type", "unknown")
        for p in all_pairs
        if p.get("_task_type")
    }

    # JSONL'e yazarken internal fields (_task_type) cikar
    with out_path.open("w", encoding="utf-8") as f:
        for pair in all_pairs:
            clean = {k: v for k, v in pair.items() if not k.startswith("_")}
            f.write(json.dumps(clean, ensure_ascii=False) + "\n")

    logger.info(
        "finetune export: %d pair (%d judge + %d few_shot) -> %s",
        len(all_pairs), len(pairs_judge), len(pairs_fewshot), out_path,
    )

    return ExportResult(
        path=str(out_path),
        total_pairs=len(all_pairs),
        from_judge=len(pairs_judge),
        from_few_shot=len(pairs_fewshot),
        task_types=sorted(task_set),
    )


def _collect_from_judge(
    min_score: float,
    task_types: Optional[list[str]],
    days: int,
) -> list[dict]:
    """llm_judge_runs + llm_traces JOIN -> yuksek skorlu pair'ler."""
    try:
        from app.domains.ai.llm_trace import _get_conn
        conn = _get_conn()
    except Exception:
        return []

    try:
        with conn.cursor() as cur:
            # Tablolar var mi?
            cur.execute(
                """
                SELECT
                    EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name = 'llm_judge_runs'),
                    EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name = 'llm_traces')
                """
            )
            row = cur.fetchone()
            if not row or not row[0] or not row[1]:
                return []

            # JOIN sorgusu: judge skor + trace icerigi
            tt_filter = ""
            params: list[Any] = [min_score, f"{int(days)} days"]
            if task_types:
                tt_filter = "AND j.task_type = ANY(%s)"
                params.append(task_types)

            cur.execute(
                f"""
                SELECT j.task_type,
                       t.system_prompt_preview,
                       t.user_prompt_preview,
                       t.response_preview,
                       j.overall
                FROM llm_judge_runs j
                LEFT JOIN llm_traces t ON t.id = j.trace_id
                WHERE j.overall >= %s
                  AND j.created_at > NOW() - INTERVAL %s
                  {tt_filter}
                ORDER BY j.overall DESC, j.created_at DESC
                LIMIT 2000
                """,
                params,
            )
            rows = cur.fetchall() or []
    except Exception as exc:
        logger.debug("_collect_from_judge hatasi: %s", exc)
        return []
    finally:
        try:
            conn.close()
        except Exception:
            pass

    pairs: list[dict] = []
    for r in rows:
        task_type, sys_prev, user_prev, resp_prev, overall = r
        if not user_prev or not resp_prev:
            continue
        messages = []
        if sys_prev:
            messages.append({"role": "system", "content": sys_prev})
        messages.append({"role": "user", "content": user_prev})
        messages.append({"role": "assistant", "content": resp_prev})
        pairs.append({
            "messages": messages,
            "_task_type": task_type,
            "_source": "judge",
            "_judge_overall": float(overall) if overall else None,
        })
    return pairs


def _collect_from_few_shot(task_types: Optional[list[str]]) -> list[dict]:
    """few_shot_examples tablosundan verified kayitlari al."""
    try:
        from app.domains.ai.llm_trace import _get_conn
        conn = _get_conn()
    except Exception:
        return []

    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name = 'few_shot_examples')"
            )
            row = cur.fetchone()
            if not row or not row[0]:
                return []

            if task_types:
                cur.execute(
                    """
                    SELECT mode, input_text, output_json, quality_score
                    FROM few_shot_examples
                    WHERE verified_by_human = TRUE
                      AND is_negative = FALSE
                      AND mode = ANY(%s)
                    ORDER BY quality_score DESC
                    """,
                    (task_types,),
                )
            else:
                cur.execute(
                    """
                    SELECT mode, input_text, output_json, quality_score
                    FROM few_shot_examples
                    WHERE verified_by_human = TRUE AND is_negative = FALSE
                    ORDER BY quality_score DESC
                    """
                )
            rows = cur.fetchall() or []
    except Exception as exc:
        logger.debug("_collect_from_few_shot hatasi: %s", exc)
        return []
    finally:
        try:
            conn.close()
        except Exception:
            pass

    pairs: list[dict] = []
    for r in rows:
        mode, input_text, output_json, score = r
        if not input_text or not output_json:
            continue
        # output_json psycopg2'den dict olarak gelir (JSONB)
        if isinstance(output_json, dict):
            assistant_content = json.dumps(output_json, ensure_ascii=False)
        else:
            assistant_content = str(output_json)

        pairs.append({
            "messages": [
                {
                    "role": "system",
                    "content": f"Bankacilik {mode} gorevi için yuksek kaliteli cikti üret.",
                },
                {"role": "user", "content": input_text},
                {"role": "assistant", "content": assistant_content},
            ],
            "_task_type": mode,
            "_source": "few_shot",
            "_quality_score": float(score) if score else None,
        })
    return pairs


def get_export_readiness() -> dict[str, Any]:
    """Kac pair export edilebilir, hangi task'lerde — dashboard için."""
    try:
        from app.domains.ai.llm_trace import _get_conn
        conn = _get_conn()
    except Exception:
        return {"ready": False, "reason": "db_unavailable"}

    try:
        with conn.cursor() as cur:
            # Judge ile
            cur.execute(
                "SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name = 'llm_judge_runs')"
            )
            has_judge = cur.fetchone()[0]

            judge_by_task = []
            total_judge = 0
            if has_judge:
                cur.execute(
                    """
                    SELECT task_type, COUNT(*) FILTER (WHERE overall >= 9) AS high,
                           COUNT(*) AS total
                    FROM llm_judge_runs
                    WHERE created_at > NOW() - INTERVAL '90 days'
                    GROUP BY task_type
                    ORDER BY high DESC
                    """
                )
                for r in cur.fetchall() or []:
                    judge_by_task.append({
                        "task_type": r[0], "high_quality": r[1], "total": r[2],
                    })
                    total_judge += r[1]

            cur.execute(
                "SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name = 'few_shot_examples')"
            )
            has_fs = cur.fetchone()[0]
            fs_count = 0
            if has_fs:
                cur.execute(
                    "SELECT COUNT(*) FROM few_shot_examples WHERE verified_by_human = TRUE AND is_negative = FALSE"
                )
                fs_count = cur.fetchone()[0]

            total = total_judge + fs_count
            return {
                "ready": total >= 100,
                "total_pairs_available": total,
                "from_judge_high_quality": total_judge,
                "from_few_shot_verified": fs_count,
                "judge_by_task": judge_by_task,
                "minimum_recommended": 500,
                "fine_tune_recommendation": (
                    "Yeterli veri var — fine-tune başarılı olabilir."
                    if total >= 500
                    else f"Sadece {total} pair — en az 500 pair onerilir. Cagri hacmi ve judge sampling artirilmali."
                ),
            }
    except Exception as exc:
        return {"ready": False, "error": str(exc)}
    finally:
        try:
            conn.close()
        except Exception:
            pass
