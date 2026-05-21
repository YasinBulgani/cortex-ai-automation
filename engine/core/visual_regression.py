"""
Visual Regression Testing Modülü
=================================
SSIM tabanlı görsel karşılaştırma, baseline yönetimi ve diff görselleştirme.
Playwright opsiyonel olarak import edilir (HAS_PLAYWRIGHT flag).
"""
from __future__ import annotations

import json
import hashlib
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np

# ── Opsiyonel bağımlılıklar ────────────────────────────────────────────────
try:
    from PIL import Image, ImageDraw, ImageFilter
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

try:
    from playwright.sync_api import sync_playwright
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False

from config.settings import settings

logger = logging.getLogger(__name__)

# Desteklenen Mavi Yaka domain'leri
NEXUSQA_DOMAINS = ["ark", "ghz", "girit", "hrnexusqa", "pex", "plus"]


# ──────────────────────────────────────────────────────────────────────────────
# SSIM Hesaplayıcı (NumPy tabanlı, scipy bağımsız)
# ──────────────────────────────────────────────────────────────────────────────
class SSIMCalculator:
    """
    Structural Similarity Index (SSIM) hesaplayıcı.
    Scipy olmadan saf NumPy ile çalışır.
    Referans: Wang et al. (2004) IEEE Trans. Image Processing.
    """

    # SSIM sabit parametreleri
    K1 = 0.01
    K2 = 0.03
    L  = 255          # piksel değer aralığı
    WINDOW_SIZE = 11  # Gaussian pencere boyutu
    SIGMA = 1.5       # Gaussian standart sapması

    @classmethod
    def _gaussian_kernel(cls) -> np.ndarray:
        """11x11 Gaussian ağırlık penceresi üretir."""
        size = cls.WINDOW_SIZE
        sigma = cls.SIGMA
        coords = np.arange(size) - size // 2
        g = np.exp(-(coords ** 2) / (2 * sigma ** 2))
        kernel = np.outer(g, g)
        return kernel / kernel.sum()

    @classmethod
    def _convolve2d(cls, img: np.ndarray, kernel: np.ndarray) -> np.ndarray:
        """
        Manuel 2D konvolüsyon (scipy.signal.convolve2d yerine).
        Kenar efektlerini azaltmak için 'valid' mod kullanır.
        """
        kh, kw = kernel.shape
        h, w = img.shape
        # Çıktı boyutu
        oh = h - kh + 1
        ow = w - kw + 1
        out = np.zeros((oh, ow), dtype=np.float64)
        for i in range(kh):
            for j in range(kw):
                out += img[i:i + oh, j:j + ow] * kernel[i, j]
        return out

    @classmethod
    def calculate(cls, img1: np.ndarray, img2: np.ndarray) -> float:
        """
        İki görüntü arasındaki SSIM değerini hesaplar.

        Args:
            img1: Referans görüntü (H x W, float64)
            img2: Karşılaştırma görüntüsü (H x W, float64)

        Returns:
            SSIM skoru [0.0, 1.0] aralığında.
        """
        if img1.shape != img2.shape:
            raise ValueError(f"Görüntü boyutları eşleşmiyor: {img1.shape} vs {img2.shape}")

        img1 = img1.astype(np.float64)
        img2 = img2.astype(np.float64)
        kernel = cls._gaussian_kernel()

        c1 = (cls.K1 * cls.L) ** 2
        c2 = (cls.K2 * cls.L) ** 2

        mu1 = cls._convolve2d(img1, kernel)
        mu2 = cls._convolve2d(img2, kernel)

        mu1_sq = mu1 ** 2
        mu2_sq = mu2 ** 2
        mu1_mu2 = mu1 * mu2

        h, w = mu1.shape
        sigma1_sq = cls._convolve2d(img1 * img1, kernel) - mu1_sq
        sigma2_sq = cls._convolve2d(img2 * img2, kernel) - mu2_sq
        sigma12  = cls._convolve2d(img1 * img2, kernel) - mu1_mu2

        numerator   = (2 * mu1_mu2 + c1) * (2 * sigma12 + c2)
        denominator = (mu1_sq + mu2_sq + c1) * (sigma1_sq + sigma2_sq + c2)

        ssim_map = numerator / (denominator + 1e-10)
        return float(np.mean(ssim_map))

    @classmethod
    def calculate_color(cls, img1: np.ndarray, img2: np.ndarray) -> float:
        """
        RGB görüntü için her kanal ayrı SSIM hesaplar, ortalamasını döner.
        """
        if img1.ndim == 2:
            return cls.calculate(img1, img2)
        scores = []
        for ch in range(img1.shape[2]):
            scores.append(cls.calculate(img1[:, :, ch], img2[:, :, ch]))
        return float(np.mean(scores))


# ──────────────────────────────────────────────────────────────────────────────
# Pixel Diff Görselleştirici
# ──────────────────────────────────────────────────────────────────────────────
class PixelDiffVisualizer:
    """
    İki görüntü arasındaki farkı görselleştirir.
    Kırmızı overlay, diff haritası ve yan yana karşılaştırma üretir.
    """

    # Fark piksellerini işaretlemek için kırmızı renk
    DIFF_COLOR = (255, 50, 50, 180)
    # Ignore bölgelerini işaretlemek için sarı renk
    IGNORE_COLOR = (255, 220, 0, 120)

    @staticmethod
    def _load_array(path: Path | str) -> np.ndarray:
        """Görüntü dosyasını NumPy dizisine dönüştürür."""
        if not HAS_PIL:
            raise RuntimeError("Pillow yüklü değil: pip install Pillow")
        img = Image.open(str(path)).convert("RGB")
        return np.array(img, dtype=np.uint8)

    @classmethod
    def create_diff_image(
        cls,
        baseline_path: Path | str,
        current_path: Path | str,
        output_path: Path | str,
        ignore_regions: list[dict] | None = None,
        threshold_px: int = 10,
    ) -> dict:
        """
        Baseline ve güncel screenshot arasındaki fark görüntüsünü üretir.

        Args:
            baseline_path: Baseline görüntü yolu
            current_path:  Güncel görüntü yolu
            output_path:   Çıktı diff görüntüsü yolu
            ignore_regions: Maskelenecek bölgeler listesi [{x,y,w,h}, ...]
            threshold_px:  Fark sayılacak minimum piksel değeri

        Returns:
            {diff_pixels, total_pixels, diff_percent, diff_path}
        """
        if not HAS_PIL:
            raise RuntimeError("Pillow yüklü değil: pip install Pillow")

        arr1 = cls._load_array(baseline_path)
        arr2 = cls._load_array(current_path)

        # Boyut uyumsuzluğunda küçük olana kırp
        h = min(arr1.shape[0], arr2.shape[0])
        w = min(arr1.shape[1], arr2.shape[1])
        arr1, arr2 = arr1[:h, :w], arr2[:h, :w]

        # Fark maskesi
        diff = np.abs(arr1.astype(int) - arr2.astype(int))
        diff_mask = np.any(diff > threshold_px, axis=2)

        # Ignore bölgelerini maskeden çıkar
        if ignore_regions:
            for region in ignore_regions:
                x, y = region.get("x", 0), region.get("y", 0)
                rw, rh = region.get("w", 0), region.get("h", 0)
                diff_mask[y:y + rh, x:x + rw] = False

        diff_pixels  = int(np.sum(diff_mask))
        total_pixels = h * w
        diff_percent = round(diff_pixels / total_pixels * 100, 4) if total_pixels else 0.0

        # Diff görüntüsü oluştur
        diff_img = Image.fromarray(arr2).convert("RGBA")
        overlay  = Image.new("RGBA", diff_img.size, (0, 0, 0, 0))
        draw     = ImageDraw.Draw(overlay)

        # Fark piksellerini kırmızıyla işaretle
        ys, xs = np.where(diff_mask)
        for y_px, x_px in zip(ys.tolist(), xs.tolist()):
            draw.point((x_px, y_px), fill=cls.DIFF_COLOR)

        # Ignore bölgelerini sarıyla göster
        if ignore_regions:
            for region in ignore_regions:
                x, y = region.get("x", 0), region.get("y", 0)
                rw, rh = region.get("w", 0), region.get("h", 0)
                draw.rectangle([x, y, x + rw, y + rh], fill=cls.IGNORE_COLOR)

        result = Image.alpha_composite(diff_img, overlay).convert("RGB")
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        result.save(str(output_path))

        return {
            "diff_pixels": diff_pixels,
            "total_pixels": total_pixels,
            "diff_percent": diff_percent,
            "diff_path": str(output_path),
        }

    @classmethod
    def create_side_by_side(
        cls,
        baseline_path: Path | str,
        current_path: Path | str,
        output_path: Path | str,
    ) -> str:
        """
        Baseline ve güncel görüntüyü yan yana bir görüntüde birleştirir.

        Returns:
            Çıktı dosyası yolu
        """
        if not HAS_PIL:
            raise RuntimeError("Pillow yüklü değil: pip install Pillow")

        img1 = Image.open(str(baseline_path)).convert("RGB")
        img2 = Image.open(str(current_path)).convert("RGB")

        max_h = max(img1.height, img2.height)
        combined_w = img1.width + img2.width + 20  # 20px ayırıcı

        canvas = Image.new("RGB", (combined_w, max_h + 40), (15, 23, 42))
        canvas.paste(img1, (0, 40))
        canvas.paste(img2, (img1.width + 20, 40))

        draw = ImageDraw.Draw(canvas)
        draw.text((10, 10), "BASELINE", fill=(148, 163, 184))
        draw.text((img1.width + 30, 10), "GÜNCEL", fill=(148, 163, 184))

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        canvas.save(str(output_path))
        return str(output_path)


# ──────────────────────────────────────────────────────────────────────────────
# Baseline Yöneticisi
# ──────────────────────────────────────────────────────────────────────────────
class BaselineManager:
    """
    Baseline screenshot'larını dosya sistemi + JSON meta ile yönetir.
    Dizin yapısı: baselines/<domain>/<test_name>/<timestamp>.png
    """

    def __init__(self, baselines_dir: Path | str | None = None):
        self.baselines_dir = Path(baselines_dir) if baselines_dir else (
            settings.BASE_DIR / "visual_baselines"
        )
        self.baselines_dir.mkdir(parents=True, exist_ok=True)
        self.meta_file = self.baselines_dir / "meta.json"
        self._meta: dict = self._load_meta()

    # ── Meta I/O ──────────────────────────────────────────────────────────────
    def _load_meta(self) -> dict:
        if self.meta_file.exists():
            try:
                return json.loads(self.meta_file.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {}

    def _save_meta(self) -> None:
        self.meta_file.write_text(
            json.dumps(self._meta, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    # ── Domain & Test yolu ────────────────────────────────────────────────────
    def _test_dir(self, domain: str, test_name: str) -> Path:
        domain = domain if domain in NEXUSQA_DOMAINS else "default"
        path = self.baselines_dir / domain / test_name
        path.mkdir(parents=True, exist_ok=True)
        return path

    # ── Baseline kaydet ───────────────────────────────────────────────────────
    def save_baseline(
        self,
        screenshot_path: Path | str,
        domain: str,
        test_name: str,
        metadata: dict | None = None,
    ) -> dict:
        """
        Yeni bir baseline kaydeder; mevcut baseline'ı arşivler.

        Returns:
            {key, path, timestamp, hash}
        """
        src = Path(screenshot_path)
        key = f"{domain}/{test_name}"
        ts  = datetime.now().strftime("%Y%m%d_%H%M%S")
        dst = self._test_dir(domain, test_name) / f"baseline_{ts}.png"

        # Eski baseline'ı arşivle
        if key in self._meta:
            old_path = Path(self._meta[key]["path"])
            if old_path.exists():
                archive = old_path.parent / "archive"
                archive.mkdir(exist_ok=True)
                old_path.rename(archive / old_path.name)

        import shutil
        shutil.copy2(str(src), str(dst))

        img_hash = hashlib.md5(dst.read_bytes()).hexdigest()
        entry = {
            "path": str(dst),
            "timestamp": ts,
            "hash": img_hash,
            "domain": domain,
            "test_name": test_name,
            "metadata": metadata or {},
        }
        self._meta[key] = entry
        self._save_meta()
        logger.info("Baseline kaydedildi: %s → %s", key, dst)
        return entry

    # ── Baseline al ───────────────────────────────────────────────────────────
    def get_baseline(self, domain: str, test_name: str) -> dict | None:
        """Kaydedilmiş baseline meta verisini döner."""
        key = f"{domain}/{test_name}"
        entry = self._meta.get(key)
        if entry and Path(entry["path"]).exists():
            return entry
        return None

    def list_baselines(self, domain: str | None = None) -> list[dict]:
        """Tüm baseline'ları veya belirli domain'e ait olanları listeler."""
        entries = list(self._meta.values())
        if domain:
            entries = [e for e in entries if e.get("domain") == domain]
        return entries

    def delete_baseline(self, domain: str, test_name: str) -> bool:
        """Baseline kaydını ve dosyasını siler."""
        key = f"{domain}/{test_name}"
        entry = self._meta.pop(key, None)
        if entry:
            p = Path(entry["path"])
            if p.exists():
                p.unlink()
            self._save_meta()
            return True
        return False


# ──────────────────────────────────────────────────────────────────────────────
# Screenshot Alıcı (Playwright)
# ──────────────────────────────────────────────────────────────────────────────
class ScreenshotCapture:
    """
    Playwright kullanarak sayfa screenshot'ı alır.
    HAS_PLAYWRIGHT False ise çalışmaz, uygun hata mesajı döner.
    """

    def __init__(
        self,
        browser_type: str = "chromium",
        headless: bool = True,
        viewport: dict | None = None,
    ):
        self.browser_type = browser_type
        self.headless = headless
        self.viewport = viewport or {"width": 1280, "height": 800}

    def capture(
        self,
        url: str,
        output_path: Path | str,
        full_page: bool = True,
        wait_for: str | None = None,
        wait_ms: int = 500,
    ) -> str:
        """
        Verilen URL'nin screenshot'ını alır.

        Args:
            url:         Hedef URL
            output_path: Kaydedilecek dosya yolu
            full_page:   Tam sayfa screenshot
            wait_for:    Bekleme seçici (CSS selector)
            wait_ms:     Ekstra bekleme süresi (ms)

        Returns:
            Kaydedilen dosya yolu
        """
        if not HAS_PLAYWRIGHT:
            raise RuntimeError(
                "Playwright yüklü değil. Kurulum: pip install playwright && playwright install"
            )
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with sync_playwright() as pw:
            launcher = getattr(pw, self.browser_type)
            browser  = launcher.launch(headless=self.headless)
            ctx      = browser.new_context(viewport=self.viewport)
            page     = ctx.new_page()
            try:
                page.goto(url, timeout=60_000)
                if wait_for:
                    page.wait_for_selector(wait_for, timeout=10_000)
                page.wait_for_timeout(wait_ms)
                page.screenshot(path=str(output_path), full_page=full_page)
            finally:
                ctx.close()
                browser.close()

        logger.info("Screenshot alındı: %s → %s", url, output_path)
        return str(output_path)


# ──────────────────────────────────────────────────────────────────────────────
# Ana Visual Regression Test Sınıfı
# ──────────────────────────────────────────────────────────────────────────────
class VisualRegressionTester:
    """
    Görsel regresyon testlerini yürüten ana sınıf.
    Baseline karşılaştırma, batch test, raporlama.

    Kullanım örneği::

        tester = VisualRegressionTester(domain="ark")
        result = tester.compare("homepage", url="https://ark.example.com")
    """

    DEFAULT_THRESHOLD = 0.95  # %95 SSIM eşiği

    def __init__(
        self,
        domain: str = "default",
        threshold: float | None = None,
        baselines_dir: Path | str | None = None,
        ignore_regions: list[dict] | None = None,
        browser_type: str = "chromium",
        headless: bool = True,
    ):
        """
        Args:
            domain:         Mavi Yaka domain adı (ark, ghz, girit, vs.)
            threshold:      Minimum SSIM eşiği (0-1)
            baselines_dir:  Baseline depo dizini
            ignore_regions: Varsayılan ignore bölgeleri
            browser_type:   Playwright tarayıcı tipi
            headless:       Headless mod
        """
        self.domain         = domain if domain in NEXUSQA_DOMAINS else "default"
        self.threshold      = threshold or self.DEFAULT_THRESHOLD
        self.ignore_regions = ignore_regions or []
        self.capture        = ScreenshotCapture(browser_type, headless)
        self.baseline_mgr   = BaselineManager(baselines_dir)
        self.visualizer     = PixelDiffVisualizer()
        self.ssim_calc      = SSIMCalculator()

        # Geçici screenshot dizini
        self.tmp_dir = settings.SCREENSHOTS_DIR / "visual_regression_tmp"
        self.tmp_dir.mkdir(parents=True, exist_ok=True)

    # ── Yardımcı: görüntü yükle → gri dizi ─────────────────────────────────
    @staticmethod
    def _to_gray(path: Path | str) -> np.ndarray:
        """Görüntüyü gri tonlamalı NumPy dizisine dönüştürür."""
        if not HAS_PIL:
            raise RuntimeError("Pillow yüklü değil: pip install Pillow")
        img = Image.open(str(path)).convert("L")
        return np.array(img, dtype=np.float64)

    @staticmethod
    def _to_rgb(path: Path | str) -> np.ndarray:
        """Görüntüyü RGB NumPy dizisine dönüştürür."""
        if not HAS_PIL:
            raise RuntimeError("Pillow yüklü değil: pip install Pillow")
        img = Image.open(str(path)).convert("RGB")
        return np.array(img, dtype=np.float64)

    @staticmethod
    def _resize_to_match(arr1: np.ndarray, arr2: np.ndarray):
        """İki diziyi daha küçük boyuta kırpar."""
        h = min(arr1.shape[0], arr2.shape[0])
        w = min(arr1.shape[1], arr2.shape[1])
        if arr1.ndim == 3:
            return arr1[:h, :w, :], arr2[:h, :w, :]
        return arr1[:h, :w], arr2[:h, :w]

    # ── Tek karşılaştırma ────────────────────────────────────────────────────
    def compare(
        self,
        test_name: str,
        url: str | None = None,
        screenshot_path: Path | str | None = None,
        update_baseline: bool = False,
        ignore_regions: list[dict] | None = None,
        full_page: bool = True,
    ) -> dict:
        """
        Mevcut durumu baseline ile karşılaştırır.

        Args:
            test_name:       Test tanımlayıcı adı
            url:             Screenshot alınacak URL (Playwright gerekir)
            screenshot_path: Hazır screenshot yolu (url yerine kullanılabilir)
            update_baseline: True ise mevcut sonucu yeni baseline olarak kaydeder
            ignore_regions:  Bu test için özel ignore bölgeleri
            full_page:       Tam sayfa screenshot (Playwright)

        Returns:
            {
              test_name, domain, ssim_score, pixel_diff_percent,
              passed, threshold, baseline_path, current_path, diff_path,
              timestamp, error
            }
        """
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        result: dict[str, Any] = {
            "test_name": test_name,
            "domain": self.domain,
            "timestamp": ts,
            "threshold": self.threshold,
            "passed": False,
            "error": None,
        }

        try:
            # 1. Güncel screenshot al/kullan
            if screenshot_path:
                current_path = Path(screenshot_path)
            elif url:
                current_path = self.tmp_dir / f"{test_name}_{ts}.png"
                self.capture.capture(url, current_path, full_page=full_page)
            else:
                raise ValueError("url veya screenshot_path parametrelerinden biri gerekli")

            result["current_path"] = str(current_path)

            # 2. Baseline al veya oluştur
            baseline_entry = self.baseline_mgr.get_baseline(self.domain, test_name)

            if update_baseline or not baseline_entry:
                entry = self.baseline_mgr.save_baseline(
                    current_path, self.domain, test_name,
                    metadata={"url": url or "", "full_page": full_page}
                )
                result.update({
                    "baseline_path": entry["path"],
                    "ssim_score": 1.0,
                    "pixel_diff_percent": 0.0,
                    "passed": True,
                    "message": "Baseline oluşturuldu/güncellendi.",
                })
                return result

            baseline_path = Path(baseline_entry["path"])
            result["baseline_path"] = str(baseline_path)

            # 3. SSIM hesapla
            gray1, gray2 = self._to_gray(baseline_path), self._to_gray(current_path)
            gray1, gray2 = self._resize_to_match(gray1, gray2)
            ssim_score = SSIMCalculator.calculate(gray1, gray2)
            result["ssim_score"] = round(ssim_score, 6)

            # 4. Pixel diff
            effective_ignore = (self.ignore_regions or []) + (ignore_regions or [])
            diff_path = self.tmp_dir / f"{test_name}_{ts}_diff.png"
            diff_info = PixelDiffVisualizer.create_diff_image(
                baseline_path, current_path, diff_path,
                ignore_regions=effective_ignore,
            )
            result.update(diff_info)

            # 5. Karar
            result["passed"] = ssim_score >= self.threshold

        except Exception as exc:
            logger.error("Visual regression hatası [%s]: %s", test_name, exc, exc_info=True)
            result["error"] = str(exc)

        return result

    # ── Toplu test ────────────────────────────────────────────────────────────
    def batch_test(self, test_cases: list[dict]) -> dict:
        """
        Birden fazla test durumunu sırayla çalıştırır.

        Args:
            test_cases: Her biri compare() argümanları içeren dict listesi
                        Örnek: [{"test_name": "homepage", "url": "..."}]

        Returns:
            {total, passed, failed, pass_rate, results}
        """
        results = []
        for case in test_cases:
            logger.info("Batch visual test: %s", case.get("test_name"))
            r = self.compare(**case)
            results.append(r)

        passed = sum(1 for r in results if r.get("passed"))
        failed = len(results) - passed
        return {
            "total": len(results),
            "passed": passed,
            "failed": failed,
            "pass_rate": round(passed / len(results) * 100, 2) if results else 0.0,
            "results": results,
            "timestamp": datetime.now().isoformat(),
            "domain": self.domain,
        }

    # ── Rapor üretimi ─────────────────────────────────────────────────────────
    def generate_report(self, batch_result: dict, output_path: Path | str | None = None) -> str:
        """
        Batch test sonuçlarından HTML rapor üretir.

        Returns:
            Üretilen HTML rapor dosyasının yolu
        """
        if output_path is None:
            reports_dir = settings.REPORTS_DIR / "visual_regression"
            reports_dir.mkdir(parents=True, exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = reports_dir / f"visual_report_{ts}.html"
        output_path = Path(output_path)

        rows = ""
        for r in batch_result.get("results", []):
            status_cls = "pass" if r.get("passed") else "fail"
            status_lbl = "GEÇTİ" if r.get("passed") else "KALDI"
            ssim = r.get("ssim_score", "—")
            diff_pct = r.get("diff_percent", "—")
            error = r.get("error") or ""
            rows += f"""
            <tr class="{status_cls}">
              <td>{r.get("test_name")}</td>
              <td><span class="badge {status_cls}">{status_lbl}</span></td>
              <td>{ssim}</td>
              <td>{diff_pct}%</td>
              <td class="error-cell">{error}</td>
            </tr>"""

        html = f"""<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8">
<title>Visual Regression Raporu — {batch_result.get('domain', '')}</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: 'Segoe UI', system-ui, sans-serif; background: #0f172a; color: #e2e8f0; }}
  header {{ background: #1e293b; border-bottom: 1px solid #334155; padding: 24px 32px; }}
  header h1 {{ font-size: 1.4rem; color: #f8fafc; }}
  header p  {{ color: #94a3b8; font-size: 0.85rem; margin-top: 4px; }}
  .stats {{ display: flex; gap: 14px; padding: 20px 32px; }}
  .stat {{ background: #1e293b; border: 1px solid #334155; border-radius: 10px;
           padding: 14px 22px; flex: 1; text-align: center; }}
  .stat .num {{ font-size: 1.8rem; font-weight: 700; }}
  .stat .lbl {{ color: #94a3b8; font-size: 0.72rem; margin-top: 4px; }}
  .passed-s .num {{ color: #22c55e; }}
  .failed-s .num {{ color: #ef4444; }}
  .total-s  .num {{ color: #60a5fa; }}
  .pct-s    .num {{ color: #a78bfa; }}
  table {{ width: calc(100% - 64px); margin: 0 32px 32px; border-collapse: collapse; }}
  th, td {{ padding: 10px 14px; text-align: left; border-bottom: 1px solid #1e293b; font-size: 0.85rem; }}
  th {{ background: #1e293b; color: #94a3b8; font-weight: 600; }}
  tr.pass td {{ background: #0a1f12; }}
  tr.fail td {{ background: #1c0a0a; }}
  .badge {{ padding: 2px 9px; border-radius: 99px; font-size: 0.72rem; font-weight: 600; }}
  .badge.pass {{ background: #14532d; color: #86efac; }}
  .badge.fail {{ background: #450a0a; color: #fca5a5; }}
  .error-cell {{ color: #f87171; font-size: 0.78rem; max-width: 300px; word-break: break-word; }}
</style>
</head>
<body>
<header>
  <h1>🖼 Visual Regression Test Raporu — {batch_result.get('domain', 'default')}</h1>
  <p>{batch_result.get('timestamp', '')} &nbsp;|&nbsp;
     Eşik: {batch_result.get('results', [{}])[0].get('threshold', self.threshold) if batch_result.get('results') else self.threshold}</p>
</header>
<div class="stats">
  <div class="stat total-s"><div class="num">{batch_result['total']}</div><div class="lbl">TOPLAM</div></div>
  <div class="stat passed-s"><div class="num">{batch_result['passed']}</div><div class="lbl">GEÇTİ</div></div>
  <div class="stat failed-s"><div class="num">{batch_result['failed']}</div><div class="lbl">KALDI</div></div>
  <div class="stat pct-s"><div class="num">{batch_result['pass_rate']}%</div><div class="lbl">BAŞARI</div></div>
</div>
<table>
  <thead>
    <tr><th>Test Adı</th><th>Durum</th><th>SSIM</th><th>Diff %</th><th>Hata</th></tr>
  </thead>
  <tbody>{rows}</tbody>
</table>
</body>
</html>"""

        output_path.write_text(html, encoding="utf-8")
        logger.info("Visual regression raporu üretildi: %s", output_path)
        return str(output_path)


# ──────────────────────────────────────────────────────────────────────────────
# Fabrika fonksiyonu
# ──────────────────────────────────────────────────────────────────────────────
def create_visual_tester(domain: str = "default", config: dict | None = None) -> VisualRegressionTester:
    """
    Config dict ile VisualRegressionTester örneği oluşturur.
    config/visual_config.json'dan gelen değerleri kullanır.
    """
    cfg = config or {}
    return VisualRegressionTester(
        domain=domain,
        threshold=cfg.get("threshold", VisualRegressionTester.DEFAULT_THRESHOLD),
        baselines_dir=cfg.get("baselines_dir"),
        ignore_regions=cfg.get("ignore_regions"),
        browser_type=cfg.get("browser_type", "chromium"),
        headless=cfg.get("headless", True),
    )
