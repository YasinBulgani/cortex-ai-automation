"""
runner.py — Allure destekli ana test çalıştırıcısı

Çalıştırma akışı:
  1. pytest --alluredir=allure-results
  2. allure generate allure-results → allure-report
  3. allure open allure-report
"""
import sys
import subprocess
import shutil
from pathlib import Path
from datetime import datetime

from rich.console import Console
from rich.panel import Panel

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from config.settings import settings

console = Console()

ALLURE_RESULTS = ROOT / "allure-results"
ALLURE_REPORT  = ROOT / "allure-report"


def check_allure_installed() -> bool:
    return shutil.which("allure") is not None


def run_pytest(markers: str = None, extra_args: list = None) -> int:
    """pytest'i --alluredir ile çalıştırır."""
    ALLURE_RESULTS.mkdir(exist_ok=True)

    cmd = [
        sys.executable, "-m", "pytest",
        "tests/",
        f"--alluredir={ALLURE_RESULTS}",
        "--tb=short",
        "-v",
        "--color=yes",
        # steps/ klasöründeki conftest ve step dosyalarını dahil et
        "--import-mode=importlib",
    ]

    if markers:
        cmd += ["-m", markers]
    if extra_args:
        cmd += extra_args

    return subprocess.run(cmd, cwd=str(ROOT)).returncode


def generate_allure_report() -> bool:
    """allure generate komutuyla HTML rapor üretir."""
    try:
        result = subprocess.run(
            ["allure", "generate", str(ALLURE_RESULTS),
             "-o", str(ALLURE_REPORT), "--clean"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
        )
        return result.returncode == 0
    except FileNotFoundError:
        return False


def open_allure_report():
    """allure open ile raporu varsayılan tarayıcıda açar."""
    subprocess.Popen(
        ["allure", "open", str(ALLURE_REPORT)],
        cwd=str(ROOT),
    )


def serve_allure_results():
    """allure serve — canlı rapor sunucusu başlatır."""
    console.print("[bold cyan]🌐 Allure sunucusu başlatılıyor...[/bold cyan]")
    subprocess.run(
        ["allure", "serve", str(ALLURE_RESULTS)],
        cwd=str(ROOT),
    )


def main():
    import argparse
    parser = argparse.ArgumentParser(description="AI Web Otomasyon Test Runner")
    parser.add_argument("-m", "--markers", default=None,
                        help="pytest marker filtresi (örn: smoke, 'not ai')")
    parser.add_argument("--serve", action="store_true",
                        help="Testleri çalıştır ve Allure sunucusunu başlat")
    parser.add_argument("--no-report", action="store_true",
                        help="Allure raporu üretme, sadece pytest çalıştır")
    args = parser.parse_args()

    console.print(Panel.fit(
        "[bold cyan]🤖 AI Web Otomasyon BDD Test Runner[/bold cyan]\n"
        f"[dim]{datetime.now().strftime('%d.%m.%Y %H:%M:%S')}[/dim]\n"
        f"[white]BASE_URL:[/white] {settings.BASE_URL}",
        border_style="cyan",
    ))

    # Allure kurulu mu?
    if not check_allure_installed():
        console.print(
            "[yellow]⚠  Allure CLI bulunamadı![/yellow]\n"
            "   Kurmak için: [bold]brew install allure[/bold]\n"
            "   pytest çalıştırılıyor ancak rapor üretilmeyecek.\n"
        )

    # pytest çalıştır
    markers = args.markers or "not ai"
    console.print(f"\n[bold]▶ pytest çalıştırılıyor (marker: [cyan]{markers}[/cyan])...[/bold]\n")
    rc = run_pytest(markers=markers)

    if args.no_report or not check_allure_installed():
        sys.exit(rc)

    # Allure rapor üret
    console.print("\n[bold yellow]📊 Allure raporu üretiliyor...[/bold yellow]")
    ok = generate_allure_report()

    if ok:
        console.print(f"[green]✓ Rapor hazır:[/green] {ALLURE_REPORT}")
        if args.serve:
            serve_allure_results()
        else:
            open_allure_report()
    else:
        console.print("[red]❌ Allure raporu üretilemedi.[/red]")
        # Fallback: allure serve
        if ALLURE_RESULTS.exists():
            console.print("[cyan]💡 Alternatif: allure serve allure-results[/cyan]")

    sys.exit(rc)


if __name__ == "__main__":
    main()
