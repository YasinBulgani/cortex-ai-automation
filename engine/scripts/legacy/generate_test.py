"""
generate_test.py — AI destekli Test Üretici CLI

Kullanım:
  python scripts/generate_test.py --url "https://example.com" --task "Login formunu doldur"
  python scripts/generate_test.py --url "https://example.com" --task "..." --save
  python scripts/generate_test.py --url "https://example.com" --task "..." --run
"""
import sys
import time
import json
import subprocess
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

# Proje kök dizinini path'e ekle
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from config.settings import settings
from core.browser import BrowserEngine
from core.ai_engine import AIEngine
from core.reporter import Reporter

console = Console()


@click.command()
@click.option("--url",   required=True,  help="Test edilecek sayfa URL'si")
@click.option("--task",  required=True,  help="Yapılacak işin açıklaması (Türkçe veya İngilizce)")
@click.option("--save",  is_flag=True,   help="Üretilen aksiyonları JSON olarak kaydet")
@click.option("--run",   is_flag=True,   help="Aksiyonları tarayıcıda hemen çalıştır")
@click.option("--gen",   is_flag=True,   help="pytest test dosyası üret ve kaydet")
@click.option("--headless", is_flag=True, default=None, help="Tarayıcıyı arayüzsüz çalıştır")
@click.option("--name",  default=None,   help="Test / dosya adı (varsayılan: ai_test)")
def main(url, task, save, run, gen, headless, name):
    """🤖 AI Web Otomasyon Test Üreticisi"""

    console.print(Panel.fit(
        f"[bold cyan]🤖 AI Test Üreticisi[/bold cyan]\n"
        f"[white]URL:[/white]  {url}\n"
        f"[white]Görev:[/white] {task}",
        border_style="cyan",
    ))

    try:
        settings.validate()
    except ValueError as e:
        console.print(f"[bold red]❌ Yapılandırma Hatası:[/bold red] {e}")
        sys.exit(1)

    ai = AIEngine()
    test_name = name or "ai_test"

    # ── Pytest dosyası üret ───────────────────────────────────────────────────
    if gen:
        console.print("\n[bold yellow]📝 pytest test dosyası üretiliyor...[/bold yellow]")
        code = ai.generate_test_file(url=url, task=task, test_name=test_name)
        out_path = settings.TESTS_DIR / f"test_{test_name}.py"
        out_path.write_text(code, encoding="utf-8")
        console.print(f"[green]✓ Test dosyası kaydedildi:[/green] {out_path}")
        console.print(Syntax(code, "python", theme="monokai", line_numbers=True))
        return

    # ── Tarayıcıyı başlat ─────────────────────────────────────────────────────
    headless_mode = headless if headless is not None else settings.HEADLESS

    with BrowserEngine(headless=headless_mode) as engine:
        console.print(f"\n[bold]🌐 {url} açılıyor...[/bold]")
        engine.navigate(url)

        # ── Aksiyonları üret ──────────────────────────────────────────────────
        console.print("\n[bold yellow]🤖 AI aksiyonlar üretiyor...[/bold yellow]")
        actions = ai.generate_actions(task, page=engine.page)

        if not actions:
            console.print("[red]❌ AI hiç aksiyon üretemedi.[/red]")
            sys.exit(1)

        # Üretilen aksiyonları göster
        _print_actions(actions)

        # ── Kaydet ────────────────────────────────────────────────────────────
        if save:
            settings.REPORTS_DIR.mkdir(exist_ok=True)
            out = settings.REPORTS_DIR / f"{test_name}_actions.json"
            out.write_text(json.dumps(actions, ensure_ascii=False, indent=2), encoding="utf-8")
            console.print(f"[green]✓ Aksiyonlar kaydedildi:[/green] {out}")

        # ── Çalıştır ──────────────────────────────────────────────────────────
        if run:
            console.print("\n[bold magenta]▶ Aksiyonlar çalıştırılıyor...[/bold magenta]")
            start = time.time()
            results = ai.execute_actions(actions, engine.page)
            elapsed = int((time.time() - start) * 1000)

            # Rapor
            reporter = Reporter(report_name=test_name)
            reporter.add_result(
                test_name=test_name,
                url=url,
                action_results=results,
                duration_ms=elapsed,
            )
            report_path = reporter.save()

            # Özet
            passed = sum(1 for r in results if r["status"] == "passed")
            failed = len(results) - passed
            _print_summary(passed, failed, elapsed, report_path)


# ── Yardımcılar ────────────────────────────────────────────────────────────────

def _print_actions(actions: list[dict]):
    table = Table(title="🎯 Üretilen Aksiyonlar", border_style="blue", show_header=True)
    table.add_column("#",      style="dim", width=4)
    table.add_column("Aksiyon", style="cyan")
    table.add_column("Detay",  style="white")
    for i, a in enumerate(actions, 1):
        act = a.get("action", "")
        detail = " | ".join(f"{k}={v}" for k, v in a.items() if k != "action")
        table.add_row(str(i), act, detail)
    console.print(table)


def _print_summary(passed: int, failed: int, elapsed: int, report_path: str):
    total = passed + failed
    pct = round(passed / total * 100) if total else 0
    color = "green" if failed == 0 else ("yellow" if pct >= 50 else "red")
    console.print(Panel(
        f"[bold {color}]{'✅ BAŞARILI' if failed == 0 else '⚠️  KISMEN BAŞARILI' if pct >= 50 else '❌ BAŞARISIZ'}[/bold {color}]\n"
        f"Toplam: {total}  |  Başarılı: {passed}  |  Başarısız: {failed}  |  Oran: %{pct}\n"
        f"Süre: {elapsed}ms\n"
        f"[dim]📄 Rapor: {report_path}[/dim]",
        border_style=color,
    ))


if __name__ == "__main__":
    main()
