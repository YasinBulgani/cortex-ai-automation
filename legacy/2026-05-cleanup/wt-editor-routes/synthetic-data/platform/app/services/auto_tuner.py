"""
Auto Tuner Modülü
=================

Bu modül, sentetik bankacılık verisi üretim parametrelerini otomatik olarak
optimize etmek için çeşitli arama stratejileri uygular.

Desteklenen Stratejiler:
    - GRID_SEARCH  : Tüm parametre kombinasyonlarını kapsamlı biçimde dener.
    - RANDOM       : Parametre uzayından rastgele örnekler alır.
    - BAYESIAN     : Gaussian Process vekil modeli + UCB kazanım fonksiyonu.
    - HYBRID       : Önce random arama, ardından Bayesian iyileştirme.

Başlıca Sınıflar:
    TuningHistory  : JSON tabanlı geçmiş saklama ve önbellekleme.
    AutoTuner      : Ana optimizasyon motoru.

Bağımlılıklar:
    numpy, typing, dataclasses, enum, logging, json, os,
    threading, time, itertools, datetime
"""

from __future__ import annotations

import itertools
import json
import logging
import os
import threading
import time
from dataclasses import dataclass, asdict, field
from datetime import datetime
from enum import Enum
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Tuple,
    Union,
)

import numpy as np

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enum: TuningStrategy
# ---------------------------------------------------------------------------

class TuningStrategy(Enum):
    """Desteklenen optimizasyon stratejileri."""
    GRID_SEARCH = "grid_search"
    BAYESIAN    = "bayesian"
    RANDOM      = "random"
    HYBRID      = "hybrid"


# ---------------------------------------------------------------------------
# Dataclass: TuningResult
# ---------------------------------------------------------------------------

@dataclass
class TuningResult:
    """
    Tek bir değerlendirme turunun sonucunu temsil eder.

    Alanlar:
        params     : Denenen parametre sözlüğü.
        score      : Hedef fonksiyondan dönen skalar skor.
        iteration  : Kaçıncı iterasyon olduğu.
        strategy   : Hangi stratejinin ürettiği.
        timestamp  : Değerlendirme zamanı.
        metadata   : Ek bilgiler (örn. hata mesajı, süre).
    """
    params:    Dict[str, Any]
    score:     float
    iteration: int
    strategy:  TuningStrategy
    timestamp: datetime
    metadata:  Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Serileştirme için sözlüğe dönüştür."""
        d = asdict(self)
        d["strategy"]  = self.strategy.value
        d["timestamp"] = self.timestamp.isoformat()
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "TuningResult":
        """Sözlükten TuningResult nesnesi oluştur."""
        return cls(
            params    = d["params"],
            score     = float(d["score"]),
            iteration = int(d["iteration"]),
            strategy  = TuningStrategy(d["strategy"]),
            timestamp = datetime.fromisoformat(d["timestamp"]),
            metadata  = d.get("metadata", {}),
        )


# ---------------------------------------------------------------------------
# Sınıf: TuningHistory
# ---------------------------------------------------------------------------

class TuningHistory:
    """
    Optimizasyon geçmişini bellekte tutar ve JSON dosyasına kaydeder.

    Özellikler:
        - Thread-safe ekleme ve sorgulama.
        - İlk başlatmada varolan önbellekten yükleme.
        - En iyi N sonucu skora göre sıralı döndürme.

    Parametreler:
        cache_path (str): Önbellek JSON dosyasının yolu.
    """

    def __init__(self, cache_path: str = "tuning_cache.json") -> None:
        """
        TuningHistory nesnesini başlat.

        Parametreler:
            cache_path (str): Geçmişin yazılacağı JSON dosyası.
        """
        self.cache_path = cache_path
        self._results: List[TuningResult] = []
        self._lock = threading.Lock()
        self.load_from_cache()

    # ------------------------------------------------------------------
    # Genel API
    # ------------------------------------------------------------------

    def add(self, result: TuningResult) -> None:
        """
        Yeni bir sonuç ekle ve önbelleği güncelle.

        Parametreler:
            result (TuningResult): Eklenecek sonuç.
        """
        with self._lock:
            self._results.append(result)
            self.save_to_cache()

    def get_best(self, n: int = 10) -> List[TuningResult]:
        """
        En yüksek skorlu N sonucu döndür.

        Parametreler:
            n (int): Döndürülecek sonuç sayısı. Varsayılan: 10.

        Döner:
            List[TuningResult]: Skora göre azalan sıralı liste.
        """
        with self._lock:
            sorted_results = sorted(
                self._results, key=lambda r: r.score, reverse=True
            )
            return sorted_results[:n]

    def all_results(self) -> List[TuningResult]:
        """Tüm sonuçların kopyasını döndür."""
        with self._lock:
            return list(self._results)

    def clear(self) -> None:
        """Bellekteki tüm geçmişi ve önbellek dosyasını sil."""
        with self._lock:
            self._results.clear()
            if os.path.exists(self.cache_path):
                try:
                    os.remove(self.cache_path)
                except OSError as exc:
                    logger.warning("Önbellek dosyası silinemedi: %s", exc)

    def load_from_cache(self) -> None:
        """
        JSON önbellek dosyasını oku ve sonuçları belleğe yükle.
        Dosya yoksa veya bozuksa sessizce devam eder.
        """
        if not os.path.exists(self.cache_path):
            return
        try:
            with open(self.cache_path, "r", encoding="utf-8") as fh:
                raw: List[dict] = json.load(fh)
            loaded = []
            for item in raw:
                try:
                    loaded.append(TuningResult.from_dict(item))
                except Exception as exc:  # noqa: BLE001
                    logger.debug("Önbellek girdisi atlandı: %s", exc)
            with self._lock:
                self._results = loaded
            logger.info(
                "%d geçmiş sonuç önbellekten yüklendi (%s).",
                len(loaded), self.cache_path,
            )
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Önbellek yüklenemedi: %s", exc)

    def save_to_cache(self) -> None:
        """
        Bellekteki tüm sonuçları JSON dosyasına yaz.
        Kilit dışarıdan alınmış varsayılır (add() içinden çağrılır).
        """
        try:
            data = [r.to_dict() for r in self._results]
            with open(self.cache_path, "w", encoding="utf-8") as fh:
                json.dump(data, fh, ensure_ascii=False, indent=2)
        except OSError as exc:
            logger.warning("Önbellek kaydedilemedi: %s", exc)

    def __len__(self) -> int:
        with self._lock:
            return len(self._results)

    def __repr__(self) -> str:
        return (
            f"TuningHistory(n_results={len(self)}, "
            f"cache_path='{self.cache_path}')"
        )


# ---------------------------------------------------------------------------
# Yardımcı: _ParamSpace
# ---------------------------------------------------------------------------

class _ParamSpace:
    """
    Parametre uzayını temsil eden iç yardımcı sınıf.

    Parametre uzayı formatları:
        - Sürekli aralık   : {"lr": (0.0001, 0.01)}
        - Ayrık liste      : {"batch": [16, 32, 64, 128]}
        - Tek değer (sabit): {"dropout": 0.5}
    """

    def __init__(self, space: Dict[str, Any]) -> None:
        self.space = space
        self.names: List[str] = list(space.keys())

    def is_continuous(self, name: str) -> bool:
        """Parametre sürekli bir aralık mı?"""
        val = self.space[name]
        return isinstance(val, tuple) and len(val) == 2

    def is_discrete(self, name: str) -> bool:
        """Parametre ayrık bir liste mi?"""
        return isinstance(self.space[name], list)

    def is_fixed(self, name: str) -> bool:
        """Parametre sabit mi?"""
        return not self.is_continuous(name) and not self.is_discrete(name)

    def sample_random(self, rng: np.random.RandomState) -> Dict[str, Any]:
        """Parametre uzayından rastgele bir nokta örnekle."""
        params: Dict[str, Any] = {}
        for name in self.names:
            val = self.space[name]
            if self.is_continuous(name):
                lo, hi = val
                params[name] = float(rng.uniform(lo, hi))
            elif self.is_discrete(name):
                params[name] = rng.choice(val)
            else:
                params[name] = val
        return params

    def grid_values(self, n_per_continuous: int = 3) -> Dict[str, List[Any]]:
        """
        Her parametre için grid değer listesi döndür.

        Parametreler:
            n_per_continuous (int): Sürekli parametreler için nokta sayısı.
        """
        grid: Dict[str, List[Any]] = {}
        for name in self.names:
            val = self.space[name]
            if self.is_continuous(name):
                lo, hi = val
                grid[name] = list(np.linspace(lo, hi, n_per_continuous))
            elif self.is_discrete(name):
                grid[name] = list(val)
            else:
                grid[name] = [val]
        return grid

    def encode(self, params: Dict[str, Any]) -> np.ndarray:
        """
        Parametre sözlüğünü Gaussian Process için sayısal diziye kodla.

        Sürekli değerler [0, 1] aralığına normalize edilir.
        Ayrık değerler indeks / (n-1) olarak kodlanır.
        """
        arr = []
        for name in self.names:
            raw = params.get(name, self._midpoint(name))
            val = self.space[name]
            if self.is_continuous(name):
                lo, hi = val
                span = hi - lo if hi != lo else 1.0
                arr.append((float(raw) - lo) / span)
            elif self.is_discrete(name):
                choices = list(val)
                idx = choices.index(raw) if raw in choices else 0
                n = max(len(choices) - 1, 1)
                arr.append(idx / n)
            else:
                arr.append(0.0)
        return np.array(arr, dtype=float)

    def decode(self, arr: np.ndarray) -> Dict[str, Any]:
        """
        Sayısal diziyi parametre sözlüğüne geri dönüştür.

        Parametreler:
            arr (np.ndarray): [0, 1] aralığında kodlanmış dizi.
        """
        params: Dict[str, Any] = {}
        for i, name in enumerate(self.names):
            val = self.space[name]
            x = float(np.clip(arr[i], 0.0, 1.0))
            if self.is_continuous(name):
                lo, hi = val
                params[name] = lo + x * (hi - lo)
            elif self.is_discrete(name):
                choices = list(val)
                idx = int(round(x * (len(choices) - 1)))
                idx = max(0, min(idx, len(choices) - 1))
                params[name] = choices[idx]
            else:
                params[name] = val
        return params

    def _midpoint(self, name: str) -> Any:
        val = self.space[name]
        if self.is_continuous(name):
            return (val[0] + val[1]) / 2.0
        if self.is_discrete(name):
            return val[len(val) // 2]
        return val


# ---------------------------------------------------------------------------
# Ana Sınıf: AutoTuner
# ---------------------------------------------------------------------------

class AutoTuner:
    """
    Otomatik Parametre Optimizasyon Motoru.

    Desteklenen Stratejiler:
        GRID_SEARCH : Parametre uzayının kartezyen çarpımında tam arama.
        RANDOM      : Rasgele örnekleme ile arama.
        BAYESIAN    : RBF çekirdekli Gaussian Process + UCB kazanım fn.
        HYBRID      : İlk %30 random, sonrası Bayesian.

    Parametreler:
        strategy (TuningStrategy)    : Kullanılacak optimizasyon stratejisi.
        objective_fn (Callable)      : Minimize/maksimize edilecek fonksiyon.
                                       param_dict -> float döndürmelidir.
        param_space (dict)           : Parametre uzayı tanımı.
        max_iterations (int)         : Toplam maksimum iterasyon sayısı.
        early_stopping_patience (int): Bu kadar iterasyon iyileşme yoksa dur.
        n_threads (int)              : Paralel değerlendirme için iş parçacığı sayısı.
        cache_path (str | None)      : Geçmiş önbelleği için dosya yolu.
        maximize (bool)              : True => skoru maksimize et (varsayılan).
        seed (int)                   : Rasgelelik için tohum değeri.

    Kullanım::

        def my_fn(params):
            return -params["lr"] ** 2  # örnek

        tuner = AutoTuner(
            strategy=TuningStrategy.BAYESIAN,
            objective_fn=my_fn,
            param_space={"lr": (0.0001, 0.1), "depth": [3, 5, 7, 10]},
            max_iterations=50,
        )
        best = tuner.tune()
        print(best.params, best.score)
    """

    def __init__(
        self,
        strategy: TuningStrategy = TuningStrategy.BAYESIAN,
        objective_fn: Optional[Callable[[Dict[str, Any]], float]] = None,
        param_space: Optional[Dict[str, Any]] = None,
        max_iterations: int = 100,
        early_stopping_patience: int = 10,
        n_threads: int = 1,
        cache_path: Optional[str] = None,
        maximize: bool = True,
        seed: int = 42,
    ) -> None:
        """
        AutoTuner nesnesini başlat.

        Parametreler:
            strategy               : Kullanılacak arama stratejisi.
            objective_fn           : Hedef fonksiyon.
            param_space            : Parametre uzayı.
            max_iterations         : Maksimum iterasyon sayısı.
            early_stopping_patience: Erken durdurma sabrı.
            n_threads              : Paralel iş parçacığı sayısı.
            cache_path             : Önbellek dosyası yolu (None => cache yok).
            maximize               : True ise skor maksimize edilir.
            seed                   : Rasgelelik tohumu.
        """
        if param_space is None:
            param_space = {
                "learning_rate": (0.0001, 0.01),
                "batch_size":    [16, 32, 64, 128, 256],
                "noise_scale":   (0.001, 0.1),
                "regularization":(0.0, 0.5),
            }

        self.strategy  = strategy
        self.objective_fn = objective_fn or (lambda p: 0.0)
        self._space    = _ParamSpace(param_space)
        self.param_space = param_space
        self.max_iterations = max_iterations
        self.early_stopping_patience = early_stopping_patience
        self.n_threads = max(1, n_threads)
        self.maximize  = maximize
        self._rng      = np.random.RandomState(seed)

        _cache = cache_path or (
            "tuning_cache.json" if cache_path is not None else None
        )
        self.history = TuningHistory(
            cache_path=_cache if _cache else "tuning_cache.json"
        )

        # Yakınsama eğrisi (her iterasyondaki en iyi skor)
        self._convergence: List[float] = []
        self._best_result: Optional[TuningResult] = None
        self._iteration   = 0

        logger.info(
            "AutoTuner başlatıldı: strateji=%s, max_iter=%d, sabır=%d",
            strategy.value, max_iterations, early_stopping_patience,
        )

    # ------------------------------------------------------------------
    # Ana Giriş Noktası
    # ------------------------------------------------------------------

    def tune(self) -> TuningResult:
        """
        Seçili stratejiye göre optimizasyonu başlat.

        Döner:
            TuningResult: Bulunan en iyi sonuç.

        Kaldırır:
            ValueError: Hedef fonksiyon tanımlanmamışsa.
        """
        logger.info("Optimizasyon başlıyor: strateji=%s", self.strategy.value)

        if self.strategy == TuningStrategy.GRID_SEARCH:
            result = self.grid_search()
        elif self.strategy == TuningStrategy.RANDOM:
            result = self.random_search(self.max_iterations)
        elif self.strategy == TuningStrategy.BAYESIAN:
            result = self.bayesian_optimize(self.max_iterations)
        elif self.strategy == TuningStrategy.HYBRID:
            n_random = max(5, self.max_iterations // 3)
            n_bayes  = self.max_iterations - n_random
            self.random_search(n_random)
            result = self.bayesian_optimize(n_bayes)
        else:
            raise ValueError(f"Bilinmeyen strateji: {self.strategy}")

        logger.info(
            "Optimizasyon tamamlandı. En iyi skor=%.6f, params=%s",
            result.score, result.params,
        )
        return result

    # ------------------------------------------------------------------
    # Grid Search
    # ------------------------------------------------------------------

    def grid_search(self) -> TuningResult:
        """
        Tüm parametre kombinasyonlarını sistematik olarak dene.

        Sürekli parametreler 5 eşit aralıklı noktaya bölünür.
        Yüksek boyutlu uzaylarda iterasyon limiti uygulanır.

        Döner:
            TuningResult: En iyi bulunan sonuç.
        """
        logger.info("Grid search başlıyor.")
        grid = self._space.grid_values(n_per_continuous=5)
        value_lists = [grid[n] for n in self._space.names]
        combinations = list(itertools.product(*value_lists))
        total = min(len(combinations), self.max_iterations)
        logger.info("Grid boyutu: %d kombinasyon (limit=%d).", len(combinations), total)

        # Karma sıra uygula - daha adil kapsam
        indices = list(range(len(combinations)))
        self._rng.shuffle(indices)

        no_improve = 0
        best_score = -np.inf if self.maximize else np.inf

        for rank, idx in enumerate(indices[:total]):
            combo = combinations[idx]
            params = {
                self._space.names[i]: combo[i]
                for i in range(len(self._space.names))
            }
            score = self._evaluate_with_timeout(params)
            result = TuningResult(
                params=params,
                score=score,
                iteration=self._iteration,
                strategy=TuningStrategy.GRID_SEARCH,
                timestamp=datetime.now(),
                metadata={"grid_rank": rank},
            )
            self._record(result)

            improved = (
                (score > best_score) if self.maximize else (score < best_score)
            )
            if improved:
                best_score = score
                no_improve = 0
            else:
                no_improve += 1

            if no_improve >= self.early_stopping_patience:
                logger.info(
                    "Erken durdurma: %d iterasyondur iyileşme yok.",
                    self.early_stopping_patience,
                )
                break

        return self._best_result or result  # type: ignore[return-value]

    # ------------------------------------------------------------------
    # Random Search
    # ------------------------------------------------------------------

    def random_search(self, n_iter: int) -> TuningResult:
        """
        Parametre uzayından rastgele örnekler alarak arama yap.

        Parametreler:
            n_iter (int): Denenecek rastgele parametre seti sayısı.

        Döner:
            TuningResult: En iyi bulunan sonuç.
        """
        logger.info("Random search başlıyor: n_iter=%d.", n_iter)
        effective = min(n_iter, self.max_iterations)
        no_improve = 0
        best_score = -np.inf if self.maximize else np.inf
        last_result: Optional[TuningResult] = None

        for i in range(effective):
            params = self._space.sample_random(self._rng)
            score  = self._evaluate_with_timeout(params)
            result = TuningResult(
                params=params,
                score=score,
                iteration=self._iteration,
                strategy=TuningStrategy.RANDOM,
                timestamp=datetime.now(),
            )
            self._record(result)
            last_result = result

            improved = (
                (score > best_score) if self.maximize else (score < best_score)
            )
            if improved:
                best_score = score
                no_improve = 0
            else:
                no_improve += 1

            if no_improve >= self.early_stopping_patience:
                logger.info("Erken durdurma (random): %d iter iyileşme yok.", i + 1)
                break

        return self._best_result or last_result  # type: ignore[return-value]

    # ------------------------------------------------------------------
    # Bayesian Optimization
    # ------------------------------------------------------------------

    def bayesian_optimize(self, n_iter: int) -> TuningResult:
        """
        Gaussian Process vekil modeli ile Bayesian optimizasyon.

        Algoritma:
            1. Geçmişteki tüm değerlendirmeleri başlangıç verisi olarak kullan.
            2. Veri yoksa 5 rastgele başlangıç noktası üret.
            3. Her iterasyonda:
               a. GP modelini mevcut gözlemlerle eğit.
               b. UCB kazanım fonksiyonunu maksimize et (çoklu rastgele start).
               c. Önerilen noktayı değerlendir, gözlemlere ekle.
            4. Erken durdurma sabrı aşılırsa dur.

        Parametreler:
            n_iter (int): Maksimum Bayesian iterasyon sayısı.

        Döner:
            TuningResult: En iyi bulunan sonuç.
        """
        logger.info("Bayesian optimizasyon başlıyor: n_iter=%d.", n_iter)
        effective = min(n_iter, self.max_iterations)

        # Mevcut gözlemleri al
        X_obs, y_obs = self._collect_observations()

        # Yeterli başlangıç noktası yoksa rastgele üret
        n_init = max(0, 5 - len(X_obs))
        if n_init > 0:
            logger.info("%d rastgele başlangıç noktası üretiliyor.", n_init)
            for _ in range(n_init):
                params = self._space.sample_random(self._rng)
                score  = self._evaluate_with_timeout(params)
                result = TuningResult(
                    params=params,
                    score=score,
                    iteration=self._iteration,
                    strategy=TuningStrategy.BAYESIAN,
                    timestamp=datetime.now(),
                    metadata={"phase": "init"},
                )
                self._record(result)
                X_obs = np.vstack([X_obs, self._space.encode(params)])
                y_obs = np.append(y_obs, score if self.maximize else -score)

        no_improve = 0
        best_score = float(np.max(y_obs)) if len(y_obs) > 0 else -np.inf
        last_result: Optional[TuningResult] = None

        for i in range(effective):
            # GP tahmin et ve UCB ile sonraki noktayı bul
            next_arr    = self._maximize_acquisition(X_obs, y_obs)
            next_params = self._space.decode(next_arr)

            score  = self._evaluate_with_timeout(next_params)
            result = TuningResult(
                params=next_params,
                score=score,
                iteration=self._iteration,
                strategy=TuningStrategy.BAYESIAN,
                timestamp=datetime.now(),
                metadata={"phase": "bayesian", "bayes_iter": i},
            )
            self._record(result)
            last_result = result

            encoded_score = score if self.maximize else -score
            X_obs = np.vstack([X_obs, self._space.encode(next_params)])
            y_obs = np.append(y_obs, encoded_score)

            improved = encoded_score > best_score
            if improved:
                best_score = encoded_score
                no_improve = 0
            else:
                no_improve += 1

            logger.debug(
                "Bayes iter %d/%d: skor=%.6f best=%.6f",
                i + 1, effective, score, best_score,
            )

            if no_improve >= self.early_stopping_patience:
                logger.info(
                    "Erken durdurma (Bayesian): %d iter iyileşme yok.", i + 1
                )
                break

        return self._best_result or last_result  # type: ignore[return-value]

    # ------------------------------------------------------------------
    # GP Çekirdek ve Tahmin
    # ------------------------------------------------------------------

    def _rbf_kernel(
        self,
        X1: np.ndarray,
        X2: np.ndarray,
        length_scale: float = 1.0,
        noise: float = 1e-6,
    ) -> np.ndarray:
        """
        Radyal Temel Fonksiyon (RBF / Gaussian) çekirdeğini hesapla.

        k(x1, x2) = exp(-||x1 - x2||^2 / (2 * l^2))

        Parametreler:
            X1 (np.ndarray)    : (n, d) boyutlu birinci nokta matrisi.
            X2 (np.ndarray)    : (m, d) boyutlu ikinci nokta matrisi.
            length_scale (float): Çekirdek uzunluk ölçeği l.
            noise (float)      : Köşegen gürültü terimi (yalnızca X1==X2 ise eklenir).

        Döner:
            np.ndarray: (n, m) boyutlu çekirdek matrisi.
        """
        # Karesel uzaklık: ||x1 - x2||^2 = ||x1||^2 + ||x2||^2 - 2*x1.x2
        X1_sq = np.sum(X1 ** 2, axis=1, keepdims=True)   # (n, 1)
        X2_sq = np.sum(X2 ** 2, axis=1, keepdims=True).T  # (1, m)
        sq_dist = X1_sq + X2_sq - 2.0 * X1 @ X2.T
        sq_dist = np.maximum(sq_dist, 0.0)

        K = np.exp(-sq_dist / (2.0 * length_scale ** 2))

        # Gürültü yalnızca eğitim-eğitim matrisine eklenir
        if X1.shape == X2.shape and np.allclose(X1, X2):
            K += noise * np.eye(len(X1))
        return K

    def _ucb_acquisition(
        self,
        mean: np.ndarray,
        std: np.ndarray,
        kappa: float = 2.576,
    ) -> np.ndarray:
        """
        Üst Güven Sınırı (UCB) kazanım fonksiyonu.

        UCB(x) = mu(x) + kappa * sigma(x)

        Parametreler:
            mean  (np.ndarray): GP tahmin ortalamaları.
            std   (np.ndarray): GP tahmin standart sapmaları.
            kappa (float)     : Keşif/sömürü dengesi katsayısı.

        Döner:
            np.ndarray: UCB değerleri.
        """
        return mean + kappa * std

    def _gaussian_process_predict(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_test:  np.ndarray,
        length_scale: float = 0.5,
        noise: float = 1e-3,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Gaussian Process ile tahmin yap.

        Standart GP koşullama formüllerini kullanır:
            mu*    = K_s^T (K + sigma^2 I)^{-1} y
            sigma* = K_ss - K_s^T (K + sigma^2 I)^{-1} K_s

        Parametreler:
            X_train (np.ndarray)  : Eğitim girdileri (n, d).
            y_train (np.ndarray)  : Eğitim çıktıları (n,).
            X_test  (np.ndarray)  : Test girdileri (m, d).
            length_scale (float)  : RBF uzunluk ölçeği.
            noise (float)         : Gürültü terimi.

        Döner:
            Tuple[np.ndarray, np.ndarray]: (ortalama, standart_sapma) boyutu (m,).
        """
        if len(X_train) == 0:
            return np.zeros(len(X_test)), np.ones(len(X_test))

        K    = self._rbf_kernel(X_train, X_train, length_scale, noise)
        K_s  = self._rbf_kernel(X_train, X_test,  length_scale, noise=0.0)
        K_ss = self._rbf_kernel(X_test,  X_test,  length_scale, noise=0.0)

        # Çözüm: alpha = (K + noise*I)^{-1} y
        try:
            K_inv = np.linalg.inv(K)
        except np.linalg.LinAlgError:
            K_inv = np.linalg.pinv(K)

        alpha = K_inv @ y_train
        mu    = K_s.T @ alpha

        # Varyans
        v     = K_inv @ K_s
        var   = np.diag(K_ss) - np.einsum("ij,ij->j", K_s, v)
        var   = np.maximum(var, 1e-10)
        sigma = np.sqrt(var)

        return mu, sigma

    # ------------------------------------------------------------------
    # Kazanım Fonksiyonu Maksimizasyonu
    # ------------------------------------------------------------------

    def _maximize_acquisition(
        self,
        X_obs: np.ndarray,
        y_obs: np.ndarray,
        n_restarts: int = 50,
    ) -> np.ndarray:
        """
        UCB kazanım fonksiyonunu maksimize ederek sonraki noktayı bul.

        Parametreler:
            X_obs (np.ndarray)  : Gözlemlenmiş girdiler (n, d).
            y_obs (np.ndarray)  : Gözlemlenmiş çıktılar (n,).
            n_restarts (int)    : Rastgele aday nokta sayısı.

        Döner:
            np.ndarray: En yüksek UCB değerli normalized nokta.
        """
        d = len(self._space.names)
        candidates = self._rng.uniform(0.0, 1.0, size=(n_restarts, d))

        mu, sigma = self._gaussian_process_predict(X_obs, y_obs, candidates)
        ucb       = self._ucb_acquisition(mu, sigma)

        best_idx = int(np.argmax(ucb))
        return candidates[best_idx]

    # ------------------------------------------------------------------
    # Parametre Kodlama / Çözme (dışa açık arayüz)
    # ------------------------------------------------------------------

    def _encode_params(self, params: Dict[str, Any]) -> np.ndarray:
        """
        Parametre sözlüğünü GP için sayısal diziye kodla.

        Parametreler:
            params (dict): Kodlanacak parametre sözlüğü.

        Döner:
            np.ndarray: [0, 1] aralığında normalize edilmiş dizi.
        """
        return self._space.encode(params)

    def _decode_params(
        self, arr: np.ndarray, param_space: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Sayısal diziyi parametre sözlüğüne çöz.

        Parametreler:
            arr (np.ndarray)        : Kodlanmış dizi.
            param_space (dict|None) : Özel parametre uzayı (None => self._space).

        Döner:
            dict: Parametre sözlüğü.
        """
        if param_space is not None:
            return _ParamSpace(param_space).decode(arr)
        return self._space.decode(arr)

    # ------------------------------------------------------------------
    # Zaman Aşımlı Değerlendirme
    # ------------------------------------------------------------------

    def _evaluate_with_timeout(
        self,
        params: Dict[str, Any],
        timeout: int = 60,
    ) -> float:
        """
        Hedef fonksiyonu zaman aşımıyla değerlendir.

        İş parçacığı tabanlı zaman aşımı uygular. Süre aşılırsa veya
        fonksiyon hata verirse 0.0 döner.

        Parametreler:
            params  (dict): Değerlendirilecek parametreler.
            timeout (int) : Saniye cinsinden maksimum süre.

        Döner:
            float: Hedef fonksiyon skoru.
        """
        result_holder: List[Optional[float]] = [None]
        exc_holder:    List[Optional[Exception]] = [None]

        def _target() -> None:
            try:
                result_holder[0] = float(self.objective_fn(params))
            except Exception as exc:  # noqa: BLE001
                exc_holder[0] = exc
                result_holder[0] = -np.inf if self.maximize else np.inf

        t = threading.Thread(target=_target, daemon=True)
        t.start()
        t.join(timeout=timeout)

        if t.is_alive():
            logger.warning(
                "Değerlendirme zaman aşımına uğradı (%ds): %s", timeout, params
            )
            return 0.0

        if exc_holder[0] is not None:
            logger.warning("Değerlendirme hatası: %s", exc_holder[0])
            return 0.0

        return result_holder[0] or 0.0

    # ------------------------------------------------------------------
    # Paralel Değerlendirme
    # ------------------------------------------------------------------

    def parallel_evaluate(
        self,
        param_list: List[Dict[str, Any]],
    ) -> List[float]:
        """
        Birden fazla parametre setini iş parçacığı havuzuyla paralel değerlendir.

        Parametreler:
            param_list (List[dict]): Değerlendirilecek parametre setleri.

        Döner:
            List[float]: Her sete karşılık gelen skorlar (aynı sırada).
        """
        scores: List[Optional[float]] = [None] * len(param_list)
        lock   = threading.Lock()

        def _worker(idx: int, params: Dict[str, Any]) -> None:
            s = self._evaluate_with_timeout(params)
            with lock:
                scores[idx] = s

        threads: List[threading.Thread] = []
        chunk = max(1, min(self.n_threads, len(param_list)))

        for i in range(0, len(param_list), chunk):
            batch = param_list[i : i + chunk]
            batch_threads = []
            for j, p in enumerate(batch):
                t = threading.Thread(
                    target=_worker, args=(i + j, p), daemon=True
                )
                batch_threads.append(t)
                t.start()
            for t in batch_threads:
                t.join()
            threads.extend(batch_threads)

        return [s if s is not None else 0.0 for s in scores]

    # ------------------------------------------------------------------
    # Sorgu Yöntemleri
    # ------------------------------------------------------------------

    def get_best_params(self) -> Optional[Dict[str, Any]]:
        """
        Tüm iterasyonlardaki en iyi parametre setini döndür.

        Döner:
            dict | None: En iyi parametreler, hiç değerlendirme yapılmamışsa None.
        """
        if self._best_result is None:
            best_list = self.history.get_best(1)
            return best_list[0].params if best_list else None
        return self._best_result.params

    def get_convergence_curve(self) -> List[float]:
        """
        Optimizasyon boyunca kaydedilen en iyi skor serisini döndür.

        Döner:
            List[float]: Her iterasyon sonrasındaki kümülatif en iyi skor.
        """
        return list(self._convergence)

    # ------------------------------------------------------------------
    # İç Yardımcılar
    # ------------------------------------------------------------------

    def _record(self, result: TuningResult) -> None:
        """Sonucu kaydet, yakınsama eğrisini ve en iyi kaydı güncelle."""
        self._iteration += 1
        self.history.add(result)

        improved = (
            self._best_result is None
            or (self.maximize and result.score > self._best_result.score)
            or (not self.maximize and result.score < self._best_result.score)
        )
        if improved:
            self._best_result = result
            logger.debug(
                "Yeni en iyi: iter=%d, skor=%.6f", self._iteration, result.score
            )

        self._convergence.append(
            self._best_result.score if self._best_result else result.score
        )

    def _collect_observations(self) -> Tuple[np.ndarray, np.ndarray]:
        """
        Geçmiş sonuçlardan eğitim verisi topla.

        Döner:
            Tuple[np.ndarray, np.ndarray]: (X, y) boyutları (n, d) ve (n,).
        """
        all_results = self.history.all_results()
        if not all_results:
            d = len(self._space.names)
            return np.empty((0, d), dtype=float), np.empty(0, dtype=float)

        X = np.array([self._space.encode(r.params) for r in all_results])
        y = np.array([
            r.score if self.maximize else -r.score for r in all_results
        ])
        return X, y

    # ------------------------------------------------------------------
    # Dunder
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return (
            f"AutoTuner(strategy={self.strategy.value}, "
            f"max_iter={self.max_iterations}, "
            f"n_evaluated={self._iteration})"
        )


# ---------------------------------------------------------------------------
# Modül düzeyinde yardımcı fonksiyonlar
# ---------------------------------------------------------------------------

def quick_tune(
    objective_fn: Callable[[Dict[str, Any]], float],
    param_space: Dict[str, Any],
    strategy: TuningStrategy = TuningStrategy.HYBRID,
    max_iterations: int = 50,
    seed: int = 0,
) -> TuningResult:
    """
    Hızlı tek seferlik tuning için kolaylık fonksiyonu.

    Parametreler:
        objective_fn   : Hedef fonksiyon.
        param_space    : Parametre uzayı.
        strategy       : Kullanılacak strateji (varsayılan: HYBRID).
        max_iterations : Maksimum iterasyon (varsayılan: 50).
        seed           : Rasgelelik tohumu.

    Döner:
        TuningResult: En iyi bulunan sonuç.

    Örnek::

        result = quick_tune(
            objective_fn=lambda p: -(p["x"] - 3)**2,
            param_space={"x": (0.0, 10.0)},
            max_iterations=30,
        )
        print(result.params)  # {'x': ~3.0}
    """
    tuner = AutoTuner(
        strategy=strategy,
        objective_fn=objective_fn,
        param_space=param_space,
        max_iterations=max_iterations,
        cache_path=None,
        seed=seed,
    )
    return tuner.tune()


def compare_strategies(
    objective_fn: Callable[[Dict[str, Any]], float],
    param_space: Dict[str, Any],
    max_iterations: int = 30,
    seed: int = 42,
) -> Dict[str, TuningResult]:
    """
    Tüm stratejileri aynı problemde karşılaştır.

    Parametreler:
        objective_fn   : Hedef fonksiyon.
        param_space    : Parametre uzayı.
        max_iterations : Her strateji için maksimum iterasyon.
        seed           : Rasgelelik tohumu.

    Döner:
        Dict[str, TuningResult]: Strateji adı -> TuningResult eşleşmesi.
    """
    results: Dict[str, TuningResult] = {}
    for strat in TuningStrategy:
        logger.info("Strateji test ediliyor: %s", strat.value)
        tuner = AutoTuner(
            strategy=strat,
            objective_fn=objective_fn,
            param_space=param_space,
            max_iterations=max_iterations,
            cache_path=None,
            seed=seed,
        )
        try:
            results[strat.value] = tuner.tune()
        except Exception as exc:  # noqa: BLE001
            logger.error("Strateji %s başarısız: %s", strat.value, exc)
    return results
