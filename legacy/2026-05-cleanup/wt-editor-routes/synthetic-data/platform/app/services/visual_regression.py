"""
Visual Regression Testing Modülü - NumPy tabanlı SSIM hesaplama, baseline yönetimi, screenshot karşılaştırma

Bu modül, web uygulamalarının görsel regresyon testlerini gerçekleştirmek için kullanılır.
SSIM (Structural Similarity Index) algoritması kullanarak iki görüntü arasındaki yapısal
benzerliği hesaplar ve piksel düzeyinde farklılıkları görselleştirir.

Temel özellikler:
- NumPy tabanlı saf Python SSIM hesaplama (scipy veya PIL gerektirmez)
- Baseline görüntü yönetimi (kaydetme, yükleme, güncelleme, listeleme)
- Piksel fark görselleştirme ve istatistik hesaplama
- Ignore bölge maskeleme (dinamik içerik için)
- Playwright ile otomatik screenshot yakalama (opsiyonel, kurulu değilse atlanır)
- Toplu test çalıştırma desteği

Kullanım:
    suite = create_visual_regression_suite("my_baselines", threshold=0.95)
    result = suite.run_full_test("https://example.com", "homepage")
    print(result["passed"], result["ssim_score"])
"""

# Opsiyonel Playwright importu - kurulu değilse atlanır
try:
    from playwright.async_api import async_playwright
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False

import numpy as np
import json
import os
import base64
import hashlib
import logging
import struct
import zlib
import asyncio
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

# Modül seviyesinde loglama yapılandırması
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s"
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# SSIMCalculator - Structural Similarity Index hesaplama
# ---------------------------------------------------------------------------

class SSIMCalculator:
    """
    SSIM (Structural Similarity Index) hesaplama sınıfı.

    SSIM algoritması, iki görüntü arasındaki yapısal benzerliği ölçer.
    İnsan görsel sistemi modeline dayanarak üç bileşeni karşılaştırır:
      - Luminans (ortalama parlaklık)
      - Kontrast (standart sapma)
      - Yapı (korelasyon katsayısı)

    Referans:
        Wang, Z., Bovik, A. C., Sheikh, H. R., & Simoncelli, E. P. (2004).
        "Image Quality Assessment: From Error Visibility to Structural Similarity"
        IEEE Transactions on Image Processing, 13(4), 600-612.

    Sabitler:
        C1 = (0.01 * 255)^2 = 6.5025  — Luminans kararlılık sabiti
        C2 = (0.03 * 255)^2 = 58.5225 — Kontrast kararlılık sabiti
    """

    # SSIM kararlılık sabitleri (Wang et al. 2004 standart değerleri)
    C1: float = (0.01 * 255) ** 2   # = 6.5025
    C2: float = (0.03 * 255) ** 2   # = 58.5225

    def __init__(self) -> None:
        """SSIMCalculator başlatıcı."""
        self.logger = logging.getLogger(self.__class__.__name__)

    def calculate(self, img1: np.ndarray, img2: np.ndarray) -> float:
        """
        İki görüntü arasındaki global SSIM skorunu hesaplar.

        Tüm görüntü üzerinde tek bir SSIM değeri döndürür. Yerel yapısal
        farklılıkları yakalamak için calculate_windowed() tercih edilebilir.

        SSIM formülü:
            SSIM(x, y) = [(2*mu_x*mu_y + C1) * (2*sigma_xy + C2)] /
                         [(mu_x^2 + mu_y^2 + C1) * (sigma_x^2 + sigma_y^2 + C2)]

        Args:
            img1: İlk görüntü (numpy array, uint8 veya float). Gri tonlama
                  veya RGB kabul edilir; RGB ise önce gri tonlamaya dönüştürülür.
            img2: İkinci görüntü (img1 ile aynı boyut ve kanal sayısı).

        Returns:
            float: SSIM skoru [-1.0, 1.0] aralığında.
                   1.0 = özdeş görüntüler, 0.0 = yapısal benzerlik yok.

        Raises:
            ValueError: Görüntü boyutları eşleşmiyorsa.
        """
        # float64'e dönüştür — nümerik hassasiyet için gerekli
        img1_f = img1.astype(np.float64)
        img2_f = img2.astype(np.float64)

        if img1_f.shape != img2_f.shape:
            raise ValueError(
                f"Görüntü boyutları eşleşmiyor: {img1_f.shape} != {img2_f.shape}. "
                "Her iki görüntü de aynı yükseklik, genişlik ve kanal sayısına sahip olmalı."
            )

        # Çok kanallı (RGB/RGBA) görüntüyü gri tonlamaya dönüştür
        if img1_f.ndim == 3:
            # ITU-R BT.601 standart luminans ağırlıkları
            luma_weights = np.array([0.2989, 0.5870, 0.1140], dtype=np.float64)
            img1_f = np.dot(img1_f[..., :3], luma_weights)
            img2_f = np.dot(img2_f[..., :3], luma_weights)

        # Luminans: global ortalama
        mu1 = float(np.mean(img1_f))
        mu2 = float(np.mean(img2_f))

        # Kontrast: global varyans
        sigma1_sq = float(np.var(img1_f))
        sigma2_sq = float(np.var(img2_f))

        # Yapı: kovaryans
        sigma12 = float(np.mean((img1_f - mu1) * (img2_f - mu2)))

        # SSIM payı ve paydası
        numerator   = (2.0 * mu1 * mu2 + self.C1) * (2.0 * sigma12 + self.C2)
        denominator = (mu1 ** 2 + mu2 ** 2 + self.C1) * (sigma1_sq + sigma2_sq + self.C2)

        if denominator == 0.0:
            # Tamamen uniform iki görüntü — özdeş kabul edilir
            return 1.0

        ssim_value = numerator / denominator
        return float(np.clip(ssim_value, -1.0, 1.0))

    def _gaussian_window(self, size: int = 11, sigma: float = 1.5) -> np.ndarray:
        """
        Normalize edilmiş 2D Gaussian çekirdeği üretir.

        SSIM'de yerel istatistikleri ağırlıklandırmak için kullanılır.
        Merkeze yakın piksellere daha yüksek ağırlık verilir.

        Gaussian formülü:
            G(x, y) = exp(-(x^2 + y^2) / (2 * sigma^2))

        Args:
            size:  Çekirdek boyutu (tek sayı önerilir, varsayılan: 11).
            sigma: Gaussian standart sapması (varsayılan: 1.5).

        Returns:
            np.ndarray: (size x size) boyutlu, toplamı 1.0 olan float64 çekirdeği.
        """
        center = size // 2
        coords = np.arange(size, dtype=np.float64) - center

        # 2D meshgrid oluştur
        x_grid, y_grid = np.meshgrid(coords, coords)

        # Gaussian değerleri hesapla
        kernel = np.exp(-(x_grid ** 2 + y_grid ** 2) / (2.0 * sigma ** 2))

        # Normalize et: toplam = 1.0
        kernel /= kernel.sum()

        return kernel

    def _convolve2d(self, img: np.ndarray, kernel: np.ndarray) -> np.ndarray:
        """
        Saf NumPy ile 2D 'same' konvolüsyon hesaplar.

        scipy.signal.convolve2d veya başka dış kütüphane kullanmadan,
        yalnızca NumPy stride tricks ile verimli konvolüsyon gerçekleştirir.
        Küçük görüntüler için döngü bazlı fallback da bulunur.

        Args:
            img:    2D float64 giriş görüntüsü (H x W).
            kernel: 2D float64 konvolüsyon çekirdeği (kh x kw).

        Returns:
            np.ndarray: Konvolüsyon sonucu — giriş ile aynı (H x W) boyutunda.
        """
        img_h, img_w = img.shape
        ker_h, ker_w = kernel.shape
        pad_h = ker_h // 2
        pad_w = ker_w // 2

        # Reflect padding — sınır artefaktlarını azaltır
        img_padded = np.pad(img, ((pad_h, pad_h), (pad_w, pad_w)), mode='reflect')

        # Stride tricks ile patch extraction (hızlı yol)
        try:
            shape = (img_h, img_w, ker_h, ker_w)
            strides = (
                img_padded.strides[0],
                img_padded.strides[1],
                img_padded.strides[0],
                img_padded.strides[1],
            )
            patches = np.lib.stride_tricks.as_strided(
                img_padded, shape=shape, strides=strides
            )
            # Einstein summation: her patch ile kernel elemanlarını çarp ve topla
            output = np.einsum('ijkl,kl->ij', patches, kernel)
        except (ValueError, MemoryError):
            # Fallback: piksel piksel konvolüsyon (yavaş ama güvenli)
            self.logger.debug("Stride tricks başarısız, döngü bazlı konvolüsyona geçiliyor.")
            output = np.zeros((img_h, img_w), dtype=np.float64)
            for i in range(img_h):
                for j in range(img_w):
                    patch = img_padded[i: i + ker_h, j: j + ker_w]
                    output[i, j] = np.sum(patch * kernel)

        return output

    def calculate_windowed(
        self,
        img1: np.ndarray,
        img2: np.ndarray,
        window_size: int = 11
    ) -> float:
        """
        Kayan Gaussian pencere ile yerel SSIM hesaplar ve ortalar.

        Her piksel etrafındaki yerel pencere için SSIM hesaplar; bu yöntem
        global SSIM'e göre yerel bozulmaları (blur, blok artefaktlar vb.)
        daha hassas yakalar.

        Args:
            img1:        İlk görüntü (uint8 veya float, gri tonlama veya RGB).
            img2:        İkinci görüntü (img1 ile aynı boyut).
            window_size: Gaussian pencere boyutu (varsayılan: 11).

        Returns:
            float: Tüm pikseller üzerinden ortalanmış yerel SSIM skoru.
        """
        img1_f = img1.astype(np.float64)
        img2_f = img2.astype(np.float64)

        # Çok kanallı görüntüyü gri tonlamaya dönüştür
        if img1_f.ndim == 3:
            luma = np.array([0.2989, 0.5870, 0.1140], dtype=np.float64)
            img1_f = np.dot(img1_f[..., :3], luma)
            img2_f = np.dot(img2_f[..., :3], luma)

        if img1_f.shape != img2_f.shape:
            raise ValueError(
                f"Görüntü boyutları eşleşmiyor: {img1_f.shape} != {img2_f.shape}"
            )

        # Gaussian pencere çekirdeği
        win = self._gaussian_window(window_size, sigma=1.5)

        # Yerel ortalamalar (Gaussian ağırlıklı)
        mu1   = self._convolve2d(img1_f, win)
        mu2   = self._convolve2d(img2_f, win)

        mu1_sq  = mu1 * mu1
        mu2_sq  = mu2 * mu2
        mu1_mu2 = mu1 * mu2

        # Yerel varyanslar: E[X^2] - (E[X])^2
        sigma1_sq = self._convolve2d(img1_f * img1_f, win) - mu1_sq
        sigma2_sq = self._convolve2d(img2_f * img2_f, win) - mu2_sq

        # Yerel kovaryans: E[XY] - E[X]*E[Y]
        sigma12   = self._convolve2d(img1_f * img2_f, win) - mu1_mu2

        # Nümerik hata nedeniyle negatif varyansları sıfırla
        sigma1_sq = np.maximum(sigma1_sq, 0.0)
        sigma2_sq = np.maximum(sigma2_sq, 0.0)

        # Piksel bazında SSIM haritası
        num = (2.0 * mu1_mu2 + self.C1) * (2.0 * sigma12 + self.C2)
        den = (mu1_sq + mu2_sq + self.C1) * (sigma1_sq + sigma2_sq + self.C2)

        ssim_map = np.where(den != 0.0, num / den, 1.0)

        return float(np.mean(ssim_map))

    def calculate_multichannel(self, img1: np.ndarray, img2: np.ndarray) -> float:
        """
        Her renk kanalı için ayrı SSIM hesaplar ve kanal ortalamasını döndürür.

        Tek kanallı (gri tonlama) görüntüler için global calculate() kullanılır.
        RGB/RGBA görüntüler için her kanalın SSIM skoru hesaplanıp ortalanır.

        Args:
            img1: İlk görüntü (H x W veya H x W x C).
            img2: İkinci görüntü (img1 ile aynı boyut).

        Returns:
            float: Kanal ortalama SSIM skoru [0.0, 1.0].
        """
        if img1.ndim < 3 or img2.ndim < 3:
            # Tek kanallı görüntü — normal hesaplama
            return self.calculate(img1, img2)

        if img1.shape != img2.shape:
            raise ValueError(
                f"Görüntü boyutları eşleşmiyor: {img1.shape} != {img2.shape}"
            )

        n_channels = img1.shape[2]
        channel_scores: List[float] = []

        for c in range(n_channels):
            score = self.calculate(img1[:, :, c], img2[:, :, c])
            channel_scores.append(score)
            self.logger.debug(f"Kanal {c} SSIM skoru: {score:.6f}")

        mean_score = float(np.mean(channel_scores))
        self.logger.info(
            f"Çok kanallı SSIM: {mean_score:.6f} | "
            f"Kanal skorları: {[round(s, 4) for s in channel_scores]}"
        )
        return mean_score


# ---------------------------------------------------------------------------
# PixelDiffVisualizer - Piksel fark hesaplama ve görselleştirme
# ---------------------------------------------------------------------------

class PixelDiffVisualizer:
    """
    Piksel düzeyinde görüntü fark hesaplama ve görselleştirme sınıfı.

    İki görüntü arasındaki farklılıkları çeşitli yöntemlerle ortaya koyar:
      - Mutlak piksel fark haritası
      - Kırmızı ile vurgulanan fark görüntüsü
      - Yan yana karşılaştırma görünümü
      - İstatistiksel fark özeti
    """

    def __init__(self) -> None:
        """PixelDiffVisualizer başlatıcı."""
        self.logger = logging.getLogger(self.__class__.__name__)

    def compute_diff(self, img1: np.ndarray, img2: np.ndarray) -> np.ndarray:
        """
        İki görüntü arasındaki mutlak piksel farkını hesaplar.

        Her piksel pozisyonu için |img1 - img2| değeri hesaplanır.
        Sonuç uint8 formatında döndürülür (değerler 0-255 aralığında).

        Args:
            img1: Referans görüntü (uint8 veya float, herhangi bir kanal sayısı).
            img2: Test görüntüsü (img1 ile aynı boyut ve kanal sayısı).

        Returns:
            np.ndarray: Mutlak fark görüntüsü (uint8, img1 ile aynı boyut).

        Raises:
            ValueError: Görüntü boyutları eşleşmiyorsa.
        """
        if img1.shape != img2.shape:
            raise ValueError(
                f"Görüntü boyutları eşleşmiyor: {img1.shape} != {img2.shape}"
            )

        diff = np.abs(img1.astype(np.float64) - img2.astype(np.float64))
        return np.clip(diff, 0, 255).astype(np.uint8)

    def highlight_differences(
        self,
        img1: np.ndarray,
        img2: np.ndarray,
        threshold: int = 10
    ) -> np.ndarray:
        """
        Threshold değerini aşan piksel farklarını kırmızı ile vurgular.

        Orijinal referans görüntüsünü kopyalar; değişen piksel bölgelerini
        parlak kırmızı (R=255, G=0, B=0) olarak işaretler.

        Args:
            img1:      Referans görüntü (kopyası çıktı tabanı olarak kullanılır).
            img2:      Test görüntüsü.
            threshold: Vurgulama için fark eşiği (0-255 arası, varsayılan: 10).
                       Düşük değer = daha hassas; yüksek değer = sadece büyük farklar.

        Returns:
            np.ndarray: Farklılıkların kırmızı ile vurgulandığı RGB görüntüsü (uint8).
        """
        if img1.shape != img2.shape:
            raise ValueError(
                f"Görüntü boyutları eşleşmiyor: {img1.shape} != {img2.shape}"
            )

        # Fark haritası hesapla
        diff = self.compute_diff(img1, img2)

        # Çıktı görüntüsünü RGB olarak hazırla
        if img1.ndim == 2:
            result = np.stack([img1, img1, img1], axis=-1).astype(np.uint8)
            diff_mask_src = diff  # zaten 2D
        else:
            result = img1[:, :, :3].copy().astype(np.uint8)
            # Tüm kanallar üzerinden maksimum fark — en kötü durumu yakala
            diff_mask_src = np.max(diff, axis=-1) if diff.ndim == 3 else diff

        # Threshold üzerindeki pikseller için boolean maske
        changed_mask = diff_mask_src > threshold

        # Kırmızı vurgulama
        result[changed_mask, 0] = 255  # R kanalı maksimum
        result[changed_mask, 1] = 0    # G kanalı sıfır
        result[changed_mask, 2] = 0    # B kanalı sıfır

        n_changed = int(np.sum(changed_mask))
        total_px  = changed_mask.size
        self.logger.debug(
            f"Vurgulanan piksel: {n_changed}/{total_px} "
            f"(%{n_changed/total_px*100:.2f}, threshold={threshold})"
        )
        return result

    def generate_side_by_side(
        self,
        img1: np.ndarray,
        img2: np.ndarray,
        diff: np.ndarray
    ) -> np.ndarray:
        """
        Referans, test ve fark görüntülerini yatay olarak yan yana birleştirir.

        Üç görüntü arasına ince gri bir ayraç çizgisi eklenir.
        Farklı boyutlardaki görüntüler siyah dolgu ile hizalanır.

        Args:
            img1: Referans (baseline) görüntüsü.
            img2: Test görüntüsü.
            diff: Fark görüntüsü (compute_diff veya highlight_differences çıktısı).

        Returns:
            np.ndarray: Yatay olarak birleştirilmiş RGB görüntüsü (uint8).
                        Genişlik = 3 * max_w + 4 (iki ayraç), Yükseklik = max_h.
        """

        def normalize_to_rgb(img: np.ndarray) -> np.ndarray:
            """Herhangi bir görüntüyü H x W x 3 uint8 formatına dönüştürür."""
            arr = img.astype(np.uint8)
            if arr.ndim == 2:
                return np.stack([arr, arr, arr], axis=-1)
            if arr.shape[2] == 4:
                return arr[:, :, :3]
            return arr[:, :, :3]

        def pad_to_size(img: np.ndarray, h: int, w: int) -> np.ndarray:
            """Görüntüyü hedef boyuta siyah dolgu ile genişletir."""
            padded = np.zeros((h, w, 3), dtype=np.uint8)
            ih, iw = img.shape[:2]
            padded[:ih, :iw, :] = img[:ih, :iw, :]
            return padded

        r1 = normalize_to_rgb(img1)
        r2 = normalize_to_rgb(img2)
        rd = normalize_to_rgb(diff)

        # Ortak tuval boyutu
        max_h = max(r1.shape[0], r2.shape[0], rd.shape[0])
        max_w = max(r1.shape[1], r2.shape[1], rd.shape[1])

        p1 = pad_to_size(r1, max_h, max_w)
        p2 = pad_to_size(r2, max_h, max_w)
        pd = pad_to_size(rd, max_h, max_w)

        # Gri ayraç (2 piksel genişlik)
        sep = np.full((max_h, 2, 3), 180, dtype=np.uint8)

        # Yatay birleştirme: [referans | ayraç | test | ayraç | fark]
        combined = np.concatenate([p1, sep, p2, sep, pd], axis=1)
        return combined

    def diff_to_base64(self, diff_array: np.ndarray) -> str:
        """
        NumPy görüntü array'ini Base64 kodlu PNG data URI'sine dönüştürür.

        PIL/Pillow gerektirmez; _array_to_png() ile minimal PNG formatı oluşturulur.

        Args:
            diff_array: Görüntü array'i (H x W gri tonlama veya H x W x 3 RGB, uint8).

        Returns:
            str: "data:image/png;base64,<B64_VERİ>" formatında PNG URI.
        """
        png_bytes = self._array_to_png(diff_array)
        b64_str   = base64.b64encode(png_bytes).decode('utf-8')
        return f"data:image/png;base64,{b64_str}"

    def _array_to_png(self, arr: np.ndarray) -> bytes:
        """
        NumPy array'ini saf Python/NumPy/zlib ile minimal PNG byte dizisine dönüştürür.

        PNG formatı (RFC 2083) temel chunk yapısını el ile oluşturur:
          PNG imzası → IHDR → IDAT (zlib sıkıştırılmış, filter None) → IEND

        Args:
            arr: Görüntü array'i (uint8, herhangi bir kanal sayısı).

        Returns:
            bytes: Geçerli PNG formatında görüntü verisi.
        """
        # Görüntüyü H x W x 3 uint8'e normalize et
        if arr.ndim == 2:
            arr = np.stack([arr, arr, arr], axis=-1)
        elif arr.shape[2] == 4:
            arr = arr[:, :, :3]
        arr = arr.astype(np.uint8)

        height, width = arr.shape[:2]

        def make_chunk(chunk_type: bytes, data: bytes) -> bytes:
            """Uzunluk + tip + veri + CRC32 yapısında PNG chunk üretir."""
            chunk_body = chunk_type + data
            crc        = struct.pack('>I', zlib.crc32(chunk_body) & 0xFFFFFFFF)
            return struct.pack('>I', len(data)) + chunk_body + crc

        # PNG imzası (8 byte, sabit)
        signature = b'\x89PNG\r\n\x1a\n'

        # IHDR: genişlik(4) + yükseklik(4) + bit_derinlik(1) + renk_tipi(1) +
        #        sıkıştırma(1) + filtre(1) + tarama(1)
        # renk_tipi=2 → RGB truecolor
        ihdr_data  = struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0)
        ihdr_chunk = make_chunk(b'IHDR', ihdr_data)

        # IDAT: her satır başına filter byte (0 = None) ekle, ardından zlib sıkıştır
        raw_rows = b''
        for row in arr:
            raw_rows += b'\x00' + row.tobytes()

        compressed  = zlib.compress(raw_rows, level=6)
        idat_chunk  = make_chunk(b'IDAT', compressed)

        # IEND: boş kapanış chunk'ı
        iend_chunk = make_chunk(b'IEND', b'')

        return signature + ihdr_chunk + idat_chunk + iend_chunk

    def compute_diff_stats(self, img1: np.ndarray, img2: np.ndarray) -> dict:
        """
        İki görüntü arasındaki fark istatistiklerini hesaplar.

        Değişen piksel sayısı ve oranı, maksimum ve ortalama fark değerleri
        ile standart sapma gibi metrikleri tek bir sözlükte toplar.

        Args:
            img1: Referans görüntü.
            img2: Test görüntüsü (img1 ile aynı boyut).

        Returns:
            dict: Anahtarlar ve anlamları:
                - max_diff       (int):   Herhangi bir kanalda maksimum piksel farkı.
                - mean_diff      (float): Tüm kanal ve piksel fark değerlerinin ortalaması.
                - changed_pixels (int):   En az bir kanalda fark > 0 olan piksel sayısı.
                - changed_percent(float): Değişen piksellerin toplam piksele oranı (%).
                - total_pixels   (int):   Görüntüdeki toplam piksel sayısı.
                - diff_std       (float): Fark değerlerinin standart sapması.
        """
        diff = self.compute_diff(img1, img2)

        # Kanal bazında maksimum farkı her piksel için al
        if diff.ndim == 3:
            diff_per_pixel = np.max(diff, axis=-1)  # (H, W)
        else:
            diff_per_pixel = diff  # (H, W)

        total_pixels   = int(diff_per_pixel.size)
        changed_pixels = int(np.sum(diff_per_pixel > 0))
        changed_pct    = round((changed_pixels / total_pixels) * 100.0, 4) if total_pixels else 0.0

        stats = {
            "max_diff":        int(np.max(diff)),
            "mean_diff":       float(round(float(np.mean(diff)), 4)),
            "changed_pixels":  changed_pixels,
            "changed_percent": changed_pct,
            "total_pixels":    total_pixels,
            "diff_std":        float(round(float(np.std(diff)), 4)),
        }
        self.logger.debug(f"Fark istatistikleri: {stats}")
        return stats


# ---------------------------------------------------------------------------
# BaselineManager - Baseline görüntü depolama ve yönetimi
# ---------------------------------------------------------------------------

class BaselineManager:
    """
    Baseline görüntü yönetim sınıfı.

    Referans görüntüleri (baseline) disk üzerinde yönetir.
    Her baseline için:
      - <safe_name>.png  → PNG görüntü dosyası
      - <safe_name>.json → Metadata (oluşturma tarihi, checksum, boyut, vs.)

    Baseline dizini yoksa otomatik olarak oluşturulur.
    """

    def __init__(self, baseline_dir: str = "baselines") -> None:
        """
        BaselineManager başlatıcı.

        Args:
            baseline_dir: Baseline dosyalarının saklanacağı dizin yolu.
                          Dizin yoksa otomatik oluşturulur.
        """
        self.baseline_dir = Path(baseline_dir)
        self.baseline_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.info(f"Baseline dizini: {self.baseline_dir.resolve()}")

    def save_baseline(
        self,
        name: str,
        image_data: bytes,
        metadata: dict
    ) -> str:
        """
        Yeni bir baseline görüntü ve metadata dosyası kaydeder.

        Aynı isimde baseline varsa üzerine yazar (güncelleme için
        update_baseline() kullanılması önerilir).

        Args:
            name:       Baseline kimlik adı (boşluk ve özel karakter içerebilir).
            image_data: PNG formatında görüntü byte verisi.
            metadata:   İsteğe bağlı ek bilgiler (url, viewport, açıklama vb.).

        Returns:
            str: Kaydedilen PNG dosyasının tam yolu.
        """
        safe = self._sanitize_name(name)
        img_path  = self.baseline_dir / f"{safe}.png"
        meta_path = self.baseline_dir / f"{safe}.json"

        # PNG dosyasını kaydet
        with open(img_path, 'wb') as fh:
            fh.write(image_data)

        # Metadata oluştur ve kaydet
        full_meta = {
            "name":       name,
            "safe_name":  safe,
            "created_at": datetime.now().isoformat(),
            "file_size":  len(image_data),
            "checksum":   hashlib.md5(image_data).hexdigest(),
            **metadata,
        }
        with open(meta_path, 'w', encoding='utf-8') as fh:
            json.dump(full_meta, fh, indent=2, ensure_ascii=False)

        self.logger.info(f"Baseline kaydedildi: '{name}' → {img_path}")
        return str(img_path)

    def load_baseline(self, name: str) -> Tuple[np.ndarray, dict]:
        """
        Kaydedilmiş bir baseline'ı disk'ten yükler.

        Args:
            name: Yüklenecek baseline'ın adı (save_baseline()'da kullanılan).

        Returns:
            Tuple[np.ndarray, dict]:
                - Görüntü array'i (H x W x 3, uint8)
                - Metadata sözlüğü

        Raises:
            FileNotFoundError: PNG dosyası bulunamazsa.
        """
        safe = self._sanitize_name(name)
        img_path  = self.baseline_dir / f"{safe}.png"
        meta_path = self.baseline_dir / f"{safe}.json"

        if not img_path.exists():
            raise FileNotFoundError(
                f"Baseline bulunamadı: '{name}' (aranan: {img_path})"
            )

        # Görüntüyü oku ve decode et
        with open(img_path, 'rb') as fh:
            raw = fh.read()
        img_array = self._image_bytes_to_array(raw)

        # Metadata oku (opsiyonel)
        metadata: dict = {}
        if meta_path.exists():
            with open(meta_path, 'r', encoding='utf-8') as fh:
                metadata = json.load(fh)

        self.logger.info(
            f"Baseline yüklendi: '{name}', boyut={img_array.shape}, "
            f"meta_keys={list(metadata.keys())}"
        )
        return img_array, metadata

    def list_baselines(self) -> List[dict]:
        """
        Baseline dizinindeki tüm baseline'ların metadata listesini döndürür.

        Yedek (_backup_) dosyaları listeye dahil edilmez.
        Sonuçlar oluşturma tarihine göre en yeniden en eskiye sıralanır.

        Returns:
            List[dict]: Her baseline için metadata bilgileri.
        """
        baselines: List[dict] = []

        for meta_path in sorted(self.baseline_dir.glob("*.json")):
            # Yedek dosyaları atla
            if "_backup_" in meta_path.name:
                continue
            try:
                with open(meta_path, 'r', encoding='utf-8') as fh:
                    meta = json.load(fh)

                img_path = meta_path.with_suffix('.png')
                meta['image_exists']      = img_path.exists()
                meta['image_path']        = str(img_path)
                if img_path.exists():
                    meta['image_size_bytes'] = img_path.stat().st_size

                baselines.append(meta)

            except (json.JSONDecodeError, IOError) as exc:
                self.logger.warning(f"Metadata okunamadı ({meta_path.name}): {exc}")

        # Oluşturma tarihine göre azalan sıra
        baselines.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        return baselines

    def delete_baseline(self, name: str) -> bool:
        """
        Belirtilen baseline'ı (PNG + JSON) diskten siler.

        Args:
            name: Silinecek baseline adı.

        Returns:
            bool: En az bir dosya silinmişse True, hiçbir şey bulunamazsa False.
        """
        safe = self._sanitize_name(name)
        deleted = False

        for ext in ('.png', '.json'):
            path = self.baseline_dir / f"{safe}{ext}"
            if path.exists():
                path.unlink()
                deleted = True
                self.logger.info(f"Baseline dosyası silindi: {path}")

        if not deleted:
            self.logger.warning(f"Silinecek baseline bulunamadı: '{name}'")
        return deleted

    def update_baseline(self, name: str, image_data: bytes) -> str:
        """
        Mevcut bir baseline'ı yeni görüntü verisiyle günceller.

        Güncellemeden önce eski PNG dosyasını zaman damgalı yedek
        olarak saklar. Metadata'ya güncelleme bilgisi ve önceki checksum
        eklenir.

        Args:
            name:       Güncellenecek baseline adı.
            image_data: Yeni PNG görüntü verisi.

        Returns:
            str: Güncellenen PNG dosyasının tam yolu.
        """
        safe      = self._sanitize_name(name)
        img_path  = self.baseline_dir / f"{safe}.png"
        meta_path = self.baseline_dir / f"{safe}.json"

        # Eski metadata'yı oku
        old_meta: dict = {}
        if meta_path.exists():
            with open(meta_path, 'r', encoding='utf-8') as fh:
                old_meta = json.load(fh)

        # Eski PNG'yi yedekle
        if img_path.exists():
            ts     = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup = self.baseline_dir / f"{safe}_backup_{ts}.png"
            with open(img_path, 'rb') as src, open(backup, 'wb') as dst:
                dst.write(src.read())
            self.logger.info(f"Eski baseline yedeklendi: {backup}")

        # Yeni PNG'yi yaz
        with open(img_path, 'wb') as fh:
            fh.write(image_data)

        # Metadata'yı güncelle
        updated_meta = {
            **old_meta,
            "updated_at":       datetime.now().isoformat(),
            "previous_checksum": old_meta.get("checksum"),
            "checksum":         hashlib.md5(image_data).hexdigest(),
            "file_size":        len(image_data),
        }
        with open(meta_path, 'w', encoding='utf-8') as fh:
            json.dump(updated_meta, fh, indent=2, ensure_ascii=False)

        self.logger.info(f"Baseline güncellendi: '{name}'")
        return str(img_path)

    def _image_bytes_to_array(self, data: bytes) -> np.ndarray:
        """
        PNG byte verisini NumPy array'e dönüştürür.

        Önce _decode_png() ile tam PNG decode denenir. Başarısız olursa
        veriyi gri tonlama görüntü olarak yorumlayan basit bir fallback
        kullanılır.

        Args:
            data: PNG formatında görüntü byte verisi.

        Returns:
            np.ndarray: Görüntü array'i (H x W x 3, uint8).
        """
        try:
            return self._decode_png(data)
        except Exception as exc:
            self.logger.warning(
                f"PNG decode başarısız (fallback kullanılıyor): {exc}"
            )
            # Fallback: ham byte'ları gri tonlama kare görüntüye çevir
            n_bytes = len(data)
            side    = max(1, int(np.sqrt(n_bytes // 3)))
            needed  = side * side * 3
            raw     = np.frombuffer(data[:needed], dtype=np.uint8)
            if len(raw) < needed:
                raw = np.pad(raw, (0, needed - len(raw)), constant_values=128)
            return raw.reshape(side, side, 3)

    def _decode_png(self, data: bytes) -> np.ndarray:
        """
        Minimal PNG decoder — struct ve zlib kullanarak PNG'yi çözer.

        Desteklenen filtre tipleri: None(0), Sub(1), Up(2), Average(3), Paeth(4).
        Desteklenen renk tipleri: Grayscale(0), RGB(2), Grayscale+Alpha(4), RGBA(6).

        Args:
            data: Geçerli PNG formatında byte verisi.

        Returns:
            np.ndarray: RGB görüntü array'i (H x W x 3, uint8).

        Raises:
            ValueError: PNG imzası geçersizse veya IDAT chunk eksikse.
        """
        PNG_MAGIC = b'\x89PNG\r\n\x1a\n'
        if not data.startswith(PNG_MAGIC):
            raise ValueError("Geçersiz PNG imzası — bu bir PNG dosyası değil.")

        pos       = 8  # İmzadan sonraki byte
        width = height = bit_depth = color_type = 0
        idat_buf  = b''

        # Chunk okuma döngüsü
        while pos + 8 <= len(data):
            length     = struct.unpack('>I', data[pos:pos+4])[0]
            chunk_type = data[pos+4:pos+8]
            chunk_data = data[pos+8: pos+8+length]
            pos       += 12 + length  # 4(len)+4(type)+N(data)+4(crc)

            if chunk_type == b'IHDR':
                width      = struct.unpack('>I', chunk_data[0:4])[0]
                height     = struct.unpack('>I', chunk_data[4:8])[0]
                bit_depth  = chunk_data[8]
                color_type = chunk_data[9]

            elif chunk_type == b'IDAT':
                idat_buf += chunk_data

            elif chunk_type == b'IEND':
                break

        if not idat_buf:
            raise ValueError("IDAT chunk bulunamadı — geçersiz PNG yapısı.")

        # Sıkıştırılmış piksel verisini aç
        raw = zlib.decompress(idat_buf)

        # Renk tipine göre kanal sayısı
        ch_map = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}
        channels = ch_map.get(color_type, 3)
        stride   = width * channels + 1  # +1 filter byte

        rows: List[np.ndarray] = []
        prev = np.zeros(width * channels, dtype=np.uint8)

        for row_idx in range(height):
            base        = row_idx * stride
            filter_type = raw[base]
            row         = np.frombuffer(raw[base+1: base+stride], dtype=np.uint8).copy()

            if filter_type == 0:    # None — dokunma
                pass
            elif filter_type == 1:  # Sub — sol komşu ekle
                for i in range(channels, len(row)):
                    row[i] = (int(row[i]) + int(row[i - channels])) & 0xFF
            elif filter_type == 2:  # Up — üst satırı ekle
                row = ((row.astype(np.int16) + prev.astype(np.int16)) & 0xFF).astype(np.uint8)
            elif filter_type == 3:  # Average — (sol + üst) / 2
                row = row.copy()
                for i in range(len(row)):
                    a = int(row[i - channels]) if i >= channels else 0
                    b = int(prev[i])
                    row[i] = (int(row[i]) + (a + b) // 2) & 0xFF
            elif filter_type == 4:  # Paeth predictor
                row = row.copy()
                for i in range(len(row)):
                    a  = int(row[i - channels]) if i >= channels else 0
                    b  = int(prev[i])
                    c  = int(prev[i - channels]) if i >= channels else 0
                    p  = a + b - c
                    pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                    pr = a if pa <= pb and pa <= pc else (b if pb <= pc else c)
                    row[i] = (int(row[i]) + pr) & 0xFF

            rows.append(row)
            prev = row.copy()

        img = np.array(rows, dtype=np.uint8).reshape(height, width, channels)

        # Tüm renk tiplerini RGB'ye dönüştür
        if channels == 1:
            img = np.stack([img[:, :, 0]] * 3, axis=-1)
        elif channels == 2:    # Grayscale + Alpha — alpha'yı at
            img = np.stack([img[:, :, 0]] * 3, axis=-1)
        elif channels == 4:    # RGBA — alpha'yı at
            img = img[:, :, :3]

        return img

    def _array_to_image_bytes(self, arr: np.ndarray) -> bytes:
        """
        NumPy array'ini PNG byte verisine dönüştürür.

        PixelDiffVisualizer._array_to_png() metodunu kullanır.

        Args:
            arr: Görüntü array'i (H x W x 3, uint8).

        Returns:
            bytes: PNG formatında görüntü verisi.
        """
        viz = PixelDiffVisualizer()
        return viz._array_to_png(arr)

    def _sanitize_name(self, name: str) -> str:
        """
        Baseline adını dosya sistemi için güvenli hale getirir.

        Boşluklar ve özel karakterler alt çizgiye dönüştürülür.
        Maksimum uzunluk 100 karakter ile sınırlanır.

        Args:
            name: Ham baseline adı.

        Returns:
            str: Dosya adı olarak kullanılabilecek güvenli string.
        """
        safe = ''.join(
            c if (c.isalnum() or c in '-_.') else '_'
            for c in name
        )
        return safe[:100]


# ---------------------------------------------------------------------------
# IgnoreRegionMasker - Dinamik içerik bölgelerini maskeleme
# ---------------------------------------------------------------------------

class IgnoreRegionMasker:
    """
    Görüntü karşılaştırmalarında yoksayılacak bölgeleri maskeleyen sınıf.

    Reklamlar, tarih/saat göstergeleri, animasyonlar veya A/B test
    varyantları gibi dinamik içerik bölgelerini siyah (sıfır) piksellerle
    doldurarak karşılaştırma dışında bırakır.
    """

    def __init__(self) -> None:
        """IgnoreRegionMasker başlatıcı."""
        self.logger = logging.getLogger(self.__class__.__name__)

    def apply_mask(self, img: np.ndarray, regions: List[dict]) -> np.ndarray:
        """
        Belirtilen dikdörtgen bölgeleri siyah piksellerle maskeler.

        Görüntü sınırlarını aşan bölgeler kırpılır; geçersiz (sıfır boyutlu)
        bölgeler sessizce atlanır.

        Args:
            img:     Maskelenecek görüntü (herhangi kanal sayısı, uint8).
            regions: Maskeleme bölgeleri listesi. Her bölge:
                     {"x": int, "y": int, "width": int, "height": int}
                     Koordinatlar piksel cinsindendir, sol-üst köşeden başlar.

        Returns:
            np.ndarray: Maskelenmiş görüntünün kopyası (orijinal değiştirilmez).
        """
        if not regions:
            return img.copy()

        masked = img.copy()
        img_h, img_w = img.shape[:2]

        for idx, region in enumerate(regions):
            x  = max(0, int(region.get('x',      0)))
            y  = max(0, int(region.get('y',      0)))
            rw = int(region.get('width',  0))
            rh = int(region.get('height', 0))

            # Görüntü sınırlarına göre kırp
            x2 = min(x + rw, img_w)
            y2 = min(y + rh, img_h)

            if x2 <= x or y2 <= y:
                self.logger.warning(f"Bölge {idx} geçersiz veya boyutsuz, atlanıyor: {region}")
                continue

            masked[y:y2, x:x2] = 0
            self.logger.debug(
                f"Bölge {idx} maskelendi: x={x}, y={y}, w={x2-x}, h={y2-y}"
            )

        return masked

    def create_diff_mask(
        self,
        regions: List[dict],
        img_shape: Tuple[int, ...]
    ) -> np.ndarray:
        """
        Ignore bölgeleri için boolean (True = maskelenmiş) harita oluşturur.

        Args:
            regions:   Maske bölgeleri listesi (apply_mask ile aynı format).
            img_shape: Hedef görüntü boyutu (H, W) veya (H, W, C).

        Returns:
            np.ndarray: (H x W) boyutlu bool array.
                        True  → bu piksel maskelendi (görmezden gelinecek)
                        False → bu piksel karşılaştırmaya dahil
        """
        h, w = img_shape[:2]
        mask = np.zeros((h, w), dtype=bool)

        for region in regions:
            x  = max(0, int(region.get('x',      0)))
            y  = max(0, int(region.get('y',      0)))
            rw = int(region.get('width',  0))
            rh = int(region.get('height', 0))
            x2 = min(x + rw, w)
            y2 = min(y + rh, h)
            if x2 > x and y2 > y:
                mask[y:y2, x:x2] = True

        return mask


# ---------------------------------------------------------------------------
# VisualRegressionTester - Ana test orkestrasyonu
# ---------------------------------------------------------------------------

class VisualRegressionTester:
    """
    Ana görsel regresyon test sınıfı.

    BaselineManager, SSIMCalculator ve PixelDiffVisualizer bileşenlerini
    orkestrasyonla bir araya getirerek tam end-to-end görsel regresyon
    testleri çalıştırır.

    Temel akış:
        1. capture_screenshot(url) → PNG bytes
        2. compare(name, png_bytes) → SSIM skoru + fark raporu
        3. Test geçti/kaldı kararı threshold'a göre verilir.
    """

    def __init__(
        self,
        baseline_manager: BaselineManager,
        ssim_calculator:  SSIMCalculator,
        threshold:        float = 0.95,
    ) -> None:
        """
        VisualRegressionTester başlatıcı.

        Args:
            baseline_manager: Baseline depolama nesnesi.
            ssim_calculator:  SSIM hesaplama nesnesi.
            threshold:        Testin "geçti" sayılması için minimum SSIM skoru
                              (0.0 – 1.0 arası, varsayılan: 0.95).
        """
        self.baseline_manager = baseline_manager
        self.ssim_calculator  = ssim_calculator
        self.threshold        = threshold
        self.visualizer       = PixelDiffVisualizer()
        self.masker           = IgnoreRegionMasker()
        self.logger           = logging.getLogger(self.__class__.__name__)
        self.logger.info(
            f"VisualRegressionTester hazır — threshold={threshold}"
        )

    def compare(
        self,
        name:           str,
        current_image:  bytes,
        ignore_regions: Optional[List[dict]] = None,
    ) -> dict:
        """
        Mevcut görüntüyü kayıtlı baseline ile karşılaştırır.

        Karşılaştırma adımları:
          1. Baseline'ı disk'ten yükle.
          2. current_image bytes'ını numpy array'e decode et.
          3. Boyut uyumsuzluğu varsa current'ı kırp/pad et.
          4. Ignore bölgelerini her iki görüntüye uygula.
          5. SSIM skorunu hesapla (multichannel).
          6. Fark istatistiklerini ve vurgulama görüntüsünü oluştur.
          7. SSIM >= threshold ise passed=True.

        Args:
            name:           Karşılaştırılacak baseline'ın adı.
            current_image:  Güncel test görüntüsünün PNG byte verisi.
            ignore_regions: Maskelenecek bölgeler listesi (opsiyonel).

        Returns:
            dict: Sonuç sözlüğü. Anahtarlar:
                - passed          (bool):  Eşiği geçti mi?
                - ssim_score      (float): Hesaplanan SSIM değeri.
                - diff_image_b64  (str):   Fark görüntüsünün Base64 PNG URI'si.
                - changed_percent (float): Değişen piksel yüzdesi.
                - baseline_name   (str):   Karşılaştırılan baseline adı.
                - threshold       (float): Kullanılan SSIM eşiği.
                - timestamp       (str):   ISO-8601 test tarihi/saati.
                - diff_stats      (dict):  Ek fark istatistikleri (hata yoksa).
                - error           (str):   Hata mesajı (hata varsa).
                - needs_baseline  (bool):  Baseline yoksa True.
        """
        result: dict = {
            "passed":          False,
            "ssim_score":      0.0,
            "diff_image_b64":  None,
            "changed_percent": 100.0,
            "baseline_name":   name,
            "threshold":       self.threshold,
            "timestamp":       datetime.now().isoformat(),
        }

        try:
            # Adım 1 — Baseline yükle
            baseline_arr, baseline_meta = self.baseline_manager.load_baseline(name)

            # Adım 2 — Güncel görüntüyü decode et
            current_arr = self.baseline_manager._image_bytes_to_array(current_image)

            # Adım 3 — Boyut uyumunu sağla
            if baseline_arr.shape != current_arr.shape:
                self.logger.warning(
                    f"Boyut uyumsuzluğu: baseline={baseline_arr.shape}, "
                    f"current={current_arr.shape}. Yeniden boyutlandırılıyor."
                )
                current_arr = self._resize_to_match(current_arr, baseline_arr.shape)

            # Adım 4 — Ignore bölgelerini maskele
            if ignore_regions:
                bl_masked  = self.masker.apply_mask(baseline_arr, ignore_regions)
                cur_masked = self.masker.apply_mask(current_arr,  ignore_regions)
            else:
                bl_masked  = baseline_arr
                cur_masked = current_arr

            # Adım 5 — SSIM hesapla
            ssim_score = self.ssim_calculator.calculate_multichannel(
                bl_masked, cur_masked
            )

            # Adım 6 — Fark istatistikleri ve vurgulama
            diff_stats      = self.visualizer.compute_diff_stats(bl_masked, cur_masked)
            diff_highlighted = self.visualizer.highlight_differences(
                bl_masked, cur_masked, threshold=10
            )
            diff_b64 = self.visualizer.diff_to_base64(diff_highlighted)

            # Adım 7 — Karar
            passed = ssim_score >= self.threshold

            result.update({
                "passed":           passed,
                "ssim_score":       round(ssim_score, 6),
                "diff_image_b64":   diff_b64,
                "changed_percent":  diff_stats["changed_percent"],
                "diff_stats":       diff_stats,
                "baseline_metadata": baseline_meta,
            })

            verdict = "GEÇTI ✓" if passed else "BAŞARISIZ ✗"
            self.logger.info(
                f"{verdict} | '{name}' | SSIM={ssim_score:.4f} "
                f"(eşik={self.threshold}) | "
                f"değişen={diff_stats['changed_percent']:.2f}%"
            )

        except FileNotFoundError as exc:
            result["error"]          = str(exc)
            result["needs_baseline"] = True
            self.logger.error(f"Baseline yok: '{name}': {exc}")

        except Exception as exc:
            result["error"] = str(exc)
            self.logger.error(
                f"Karşılaştırma hatası: '{name}': {exc}", exc_info=True
            )

        return result

    def batch_test(self, test_cases: List[dict]) -> dict:
        """
        Birden fazla görsel regresyon testini sıralı olarak çalıştırır.

        Args:
            test_cases: Test senaryoları listesi. Her öğe:
                {
                    "name":           str   — baseline adı (zorunlu),
                    "image":          bytes — PNG verisi (zorunlu),
                    "ignore_regions": list  — maskeleme bölgeleri (opsiyonel)
                }

        Returns:
            dict:
                - total       (int):   Toplam test sayısı.
                - passed      (int):   Başarılı test sayısı.
                - failed      (int):   Başarısız test sayısı.
                - pass_rate   (float): Başarı yüzdesi.
                - duration_ms (float): Toplam süre (milisaniye).
                - results     (list):  Her test için compare() çıktısı.
                - timestamp   (str):   Toplu test tamamlanma zamanı.
        """
        start     = datetime.now()
        results   : List[dict] = []
        n_passed  = 0
        n_failed  = 0
        n_total   = len(test_cases)

        self.logger.info(f"Toplu test başlıyor: {n_total} senaryo")

        for i, tc in enumerate(test_cases, start=1):
            tc_name    = tc.get('name',           f'test_{i}')
            tc_image   = tc.get('image',          b'')
            tc_ignores = tc.get('ignore_regions', [])

            self.logger.info(f"[{i}/{n_total}] Test: '{tc_name}'")
            outcome = self.compare(tc_name, tc_image, tc_ignores)
            outcome['name'] = tc_name
            results.append(outcome)

            if outcome.get('passed', False):
                n_passed += 1
            else:
                n_failed += 1

        elapsed_ms = (datetime.now() - start).total_seconds() * 1000.0
        pass_rate  = round((n_passed / n_total) * 100.0, 2) if n_total else 0.0

        summary = {
            "total":       n_total,
            "passed":      n_passed,
            "failed":      n_failed,
            "pass_rate":   pass_rate,
            "duration_ms": round(elapsed_ms, 2),
            "results":     results,
            "timestamp":   datetime.now().isoformat(),
        }
        self.logger.info(
            f"Toplu test tamamlandı: {n_passed}/{n_total} başarılı "
            f"({pass_rate}%) | Süre: {elapsed_ms:.1f}ms"
        )
        return summary

    def capture_screenshot(
        self,
        url:      str,
        viewport: Optional[dict] = None,
    ) -> bytes:
        """
        Belirtilen URL'den tarayıcı screenshot'ı alır.

        Playwright kurulu ise headless Chromium ile gerçek screenshot alınır.
        Kurulu değilse uyarı loglanır ve placeholder PNG döndürülür.

        Args:
            url:      Screenshot alınacak tam URL (http/https zorunlu).
            viewport: Tarayıcı pencere boyutu {"width": int, "height": int}.
                      Varsayılan: {"width": 1280, "height": 720}.

        Returns:
            bytes: PNG formatında screenshot verisi.
        """
        default_vp = {"width": 1280, "height": 720}
        if viewport:
            default_vp.update(viewport)

        if not HAS_PLAYWRIGHT:
            self.logger.warning(
                "Playwright kurulu değil. "
                "Placeholder PNG döndürülüyor. "
                "Kurulum: pip install playwright && playwright install"
            )
            return self._create_placeholder_png(
                default_vp['width'],
                default_vp['height']
            )

        # Playwright async fonksiyonunu senkron olarak çalıştır
        try:
            try:
                loop = asyncio.get_running_loop()
                # Zaten çalışan loop içindeyiz — thread pool kullan
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                    future = pool.submit(
                        asyncio.run,
                        _capture_with_playwright(url, default_vp)
                    )
                    return future.result(timeout=60)
            except RuntimeError:
                # Çalışan loop yok — doğrudan asyncio.run
                return asyncio.run(_capture_with_playwright(url, default_vp))
        except Exception as exc:
            self.logger.error(f"Screenshot yakalama başarısız ({url}): {exc}")
            raise

    def run_full_test(self, url: str, name: str) -> dict:
        """
        URL'den screenshot alarak tam görsel regresyon testi çalıştırır.

        - Baseline yoksa: screenshot alıp yeni baseline oluşturur.
        - Baseline varsa: mevcut screenshot ile karşılaştırma yapar.

        Args:
            url:  Test edilecek tam URL.
            name: Baseline/test adı.

        Returns:
            dict: Baseline oluşturulduysa: {"action": "baseline_created", ...}
                  Karşılaştırma yapıldıysa: compare() çıktısı + {"url": str}
        """
        self.logger.info(f"Tam test başlıyor: '{name}' ({url})")

        # Screenshot al
        screenshot = self.capture_screenshot(url)

        # Baseline mevcudiyetini kontrol et
        baseline_exists = True
        try:
            self.baseline_manager.load_baseline(name)
        except FileNotFoundError:
            baseline_exists = False

        if not baseline_exists:
            # İlk çalıştırma — baseline oluştur
            saved = self.baseline_manager.save_baseline(
                name,
                screenshot,
                {"url": url, "source": "auto_capture"},
            )
            return {
                "action":        "baseline_created",
                "baseline_path": saved,
                "name":          name,
                "url":           url,
                "timestamp":     datetime.now().isoformat(),
                "message":       f"İlk baseline oluşturuldu: {saved}",
            }

        # Baseline var — karşılaştır
        result = self.compare(name, screenshot)
        result["url"] = url
        return result

    # ------------------------------------------------------------------
    # Yardımcı metodlar
    # ------------------------------------------------------------------

    def _resize_to_match(
        self,
        img:          np.ndarray,
        target_shape: tuple,
    ) -> np.ndarray:
        """
        Görüntüyü hedef boyuta kırpma/sıfır-dolgu ile uyarlar.

        Gerçek bir yeniden örnekleme (interpolation) yerine basit kırpma
        ve sıfır dolgu kullanılır — SSIM karşılaştırmasında sınır pikselleri
        sistematik hata yaratmaz.

        Args:
            img:          Yeniden boyutlandırılacak görüntü.
            target_shape: Hedef (H, W, C) boyutu.

        Returns:
            np.ndarray: Hedef boyutla eşleşen uint8 görüntü.
        """
        th, tw = target_shape[:2]
        tc     = target_shape[2] if len(target_shape) > 2 else 3

        # Kaynak görüntüyü RGB'ye çevir
        if img.ndim == 2:
            src = np.stack([img] * tc, axis=-1)
        elif img.shape[2] < tc:
            src = np.pad(img, ((0,0),(0,0),(0, tc - img.shape[2])))
        else:
            src = img[:, :, :tc]
        src = src.astype(np.uint8)

        # Hedef canvas oluştur
        canvas = np.zeros((th, tw, tc), dtype=np.uint8)
        ch = min(src.shape[0], th)
        cw = min(src.shape[1], tw)
        canvas[:ch, :cw] = src[:ch, :cw]
        return canvas

    def _create_placeholder_png(
        self,
        width:  int = 1280,
        height: int = 720,
    ) -> bytes:
        """
        Playwright olmadığında döndürülen test amaçlı placeholder PNG oluşturur.

        Args:
            width:  Genişlik (piksel).
            height: Yükseklik (piksel).

        Returns:
            bytes: Gri zemin üzerinde kırmızı kare içeren PNG verisi.
        """
        arr = np.full((height, width, 3), 128, dtype=np.uint8)

        # Ortaya belirteç kare
        cx, cy = width // 2, height // 2
        sz     = min(60, width // 4, height // 4)
        arr[cy - sz: cy + sz, cx - sz: cx + sz] = [200, 80, 80]

        viz = PixelDiffVisualizer()
        return viz._array_to_png(arr)

    def update_baseline_if_approved(
        self,
        name:          str,
        current_image: bytes,
    ) -> dict:
        """
        İnsan onayından sonra baseline'ı günceller.

        Yeni görüntüyü mevcut baseline ile değiştirir ve güncelleme
        bilgisini döndürür.

        Args:
            name:          Güncellenecek baseline adı.
            current_image: Yeni PNG verisi.

        Returns:
            dict: {"updated": True, "baseline_name": str, "path": str, "timestamp": str}
        """
        path = self.baseline_manager.update_baseline(name, current_image)
        return {
            "updated":        True,
            "baseline_name":  name,
            "path":           path,
            "timestamp":      datetime.now().isoformat(),
        }


# ---------------------------------------------------------------------------
# Opsiyonel Playwright async screenshot fonksiyonu
# ---------------------------------------------------------------------------

if HAS_PLAYWRIGHT:
    async def _capture_with_playwright(
        url:      str,
        viewport: Optional[dict] = None,
    ) -> bytes:
        """
        Playwright Chromium ile asenkron screenshot yakalar.

        Yalnızca HAS_PLAYWRIGHT=True ise tanımlanır.

        Args:
            url:      Screenshot alınacak tam URL.
            viewport: Tarayıcı boyutu {"width": int, "height": int}.

        Returns:
            bytes: PNG formatında screenshot.
        """
        vp = {"width": 1280, "height": 720}
        if viewport:
            vp.update(viewport)

        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True)
            context = await browser.new_context(
                viewport=vp,
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/122.0.0.0 Safari/537.36"
                ),
            )
            page = await context.new_page()
            try:
                await page.goto(url, wait_until="networkidle", timeout=30_000)
                await page.wait_for_load_state("domcontentloaded")
                png_bytes = await page.screenshot(full_page=False, type="png")
                return png_bytes
            finally:
                await browser.close()

    # VisualRegressionTester üzerine statik metod olarak ekle
    VisualRegressionTester._capture_with_playwright = staticmethod(
        _capture_with_playwright
    )

else:
    async def _capture_with_playwright(
        url:      str,
        viewport: Optional[dict] = None,
    ) -> bytes:
        """
        Playwright kurulu olmadığında boş bytes döndüren stub.

        Playwright kurulumu: pip install playwright && playwright install
        """
        raise RuntimeError(
            "Playwright kurulu değil. Kurulum: "
            "pip install playwright && playwright install chromium"
        )


# ---------------------------------------------------------------------------
# Yardımcı fabrika fonksiyonu
# ---------------------------------------------------------------------------

def create_visual_regression_suite(
    baseline_dir: str   = "baselines",
    threshold:    float = 0.95,
) -> VisualRegressionTester:
    """
    Önceden yapılandırılmış VisualRegressionTester nesnesi oluşturur.

    Tek satırda kullanıma hazır test suite'i döndüren kolaylık fonksiyonu.

    Args:
        baseline_dir: Baseline depolama dizini (varsayılan: "baselines").
        threshold:    SSIM geçme eşiği 0.0–1.0 (varsayılan: 0.95).

    Returns:
        VisualRegressionTester: Yapılandırılmış, kullanıma hazır test nesnesi.

    Örnek::

        suite = create_visual_regression_suite("my_baselines", threshold=0.97)
        result = suite.run_full_test("https://example.com", "homepage")
        print("Geçti mi?", result["passed"])
    """
    bm     = BaselineManager(baseline_dir)
    calc   = SSIMCalculator()
    tester = VisualRegressionTester(bm, calc, threshold)

    logger.info(
        f"Visual Regression Suite hazır | "
        f"baseline_dir='{baseline_dir}' | threshold={threshold}"
    )
    return tester


# ---------------------------------------------------------------------------
# Demo / quick-test
# ---------------------------------------------------------------------------

def run_visual_regression_demo() -> None:
    """
    Modülün temel işlevselliğini sentetik görüntülerle test eden demo.

    Dış bağımlılık (Playwright, PIL vb.) gerektirmez. Çalıştırmak için:
        python visual_regression.py
    """
    import tempfile

    print("=" * 60)
    print(" Görsel Regresyon Testi Modülü — Demo")
    print("=" * 60)

    rng = np.random.default_rng(42)

    # Sentetik test görüntüleri
    img_ref  = rng.integers(0, 256, (120, 160, 3), dtype=np.uint8)
    img_test = img_ref.copy()
    # Küçük kırmızı kutu ekle — görsel fark
    img_test[40:70, 60:100] = [255, 30, 30]

    # ── SSIMCalculator ──────────────────────────────────────────────
    calc   = SSIMCalculator()
    s_glob = calc.calculate(img_ref, img_test)
    s_wind = calc.calculate_windowed(img_ref, img_test)
    s_mult = calc.calculate_multichannel(img_ref, img_test)

    print(f"\n[SSIM Skorları]")
    print(f"  Global:      {s_glob:.4f}")
    print(f"  Windowed:    {s_wind:.4f}")
    print(f"  Multichannel:{s_mult:.4f}")

    # ── PixelDiffVisualizer ─────────────────────────────────────────
    viz   = PixelDiffVisualizer()
    stats = viz.compute_diff_stats(img_ref, img_test)
    print(f"\n[Fark İstatistikleri]")
    for k, v in stats.items():
        print(f"  {k}: {v}")

    hl  = viz.highlight_differences(img_ref, img_test, threshold=15)
    sbs = viz.generate_side_by_side(img_ref, img_test, hl)
    b64 = viz.diff_to_base64(hl)
    print(f"\n  Vurgulama boyutu:    {hl.shape}")
    print(f"  Yan yana boyutu:     {sbs.shape}")
    print(f"  Base64 URI uzunluğu: {len(b64)} karakter")

    # ── BaselineManager ─────────────────────────────────────────────
    with tempfile.TemporaryDirectory() as tmpdir:
        bm      = BaselineManager(tmpdir)
        png_ref = viz._array_to_png(img_ref)

        path = bm.save_baseline("anasayfa", png_ref, {"url": "https://example.com"})
        print(f"\n[BaselineManager]")
        print(f"  Kaydedildi: {path}")

        arr, meta = bm.load_baseline("anasayfa")
        print(f"  Yüklendi: shape={arr.shape}, meta_keys={list(meta.keys())}")

        listing = bm.list_baselines()
        print(f"  Toplam baseline: {len(listing)}")

        del_ok = bm.delete_baseline("anasayfa")
        print(f"  Silindi: {del_ok}")

    # ── IgnoreRegionMasker ──────────────────────────────────────────
    masker  = IgnoreRegionMasker()
    regions = [{"x": 10, "y": 10, "width": 50, "height": 30}]
    masked  = masker.apply_mask(img_ref, regions)
    print(f"\n[IgnoreRegionMasker]")
    print(f"  Maskelenmiş piksel toplamı (bölgede): {int(np.sum(masked[10:40, 10:60]))}")

    print("\nDemo başarıyla tamamlandı.")


if __name__ == "__main__":
    run_visual_regression_demo()
