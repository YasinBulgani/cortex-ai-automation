"""
GAN Discriminator Modülü

Bu modül, sentez edilmiş bankacılık verilerinin kalitesini değerlendirmek için
tamamen NumPy tabanlı bir GAN ayrımcı ağı (discriminator) uygular.
Gerçek ve sentetik veriler arasındaki farkı öğrenen sinir ağı mimarisi,
veri kalitesi puanlaması, istatistiksel testler ve kapsamlı raporlama
işlevselliği içerir.

Başlıca Sınıflar:
    SimpleNeuralNetwork : Saf NumPy sinir ağı (ileri/geri yayılım, BCE kaybı)
    GANDiscriminator    : Tam eğitim döngüsü, değerlendirme, özellik önemi
    StatisticalValidator: KS testi, Ki-kare, Wasserstein mesafesi, korelasyon
    DiscriminatorReport : İnsan okunabilir ve JSON serileştirilebilir raporlar

Kullanım:
    >>> discriminator = GANDiscriminator(hidden_layers=[128, 64, 32])
    >>> discriminator.train(real_df, synthetic_df)
    >>> report = DiscriminatorReport.generate(discriminator, validator, real_df, syn_df)
    >>> print(report.summary_text())

Notlar:
    - Tüm hesaplamalar saf NumPy ile yapılmaktadır (PyTorch/TensorFlow yoktur).
    - Kategorik sütunlar otomatik olarak kodlanır.
    - Sayısal sütunlar min-maks veya z-skor normalizasyonu ile ölçeklenir.
"""

import numpy as np
import pandas as pd
import logging
import json
from typing import Dict, List, Tuple, Any, Optional, Union
from dataclasses import dataclass, field, asdict
from datetime import datetime
from collections import defaultdict

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Yardımcı sabitler
# ---------------------------------------------------------------------------
_EPS = 1e-8  # Sayısal kararlılık için küçük değer


# ===========================================================================
# Veri Sınıfları
# ===========================================================================

@dataclass
class DiscriminatorMetrics:
    """
    Discriminator değerlendirme metriklerini tutan veri sınıfı.

    Alanlar:
        accuracy          : Doğruluk oranı (0-1)
        precision         : Kesinlik oranı (0-1)
        recall            : Duyarlılık oranı (0-1)
        f1_score          : F1 skoru (0-1)
        auc_roc           : AUC-ROC değeri (0-1)
        discriminator_score: Sentez kalite puanı (0.5 mükemmel = ayırt edilemez)
        feature_importance : Özellik adı → önem puanı sözlüğü
        loss_history      : Eğitim kaybı geçmişi
        accuracy_history  : Eğitim doğruluk geçmişi
    """

    accuracy: float = 0.0
    precision: float = 0.0
    recall: float = 0.0
    f1_score: float = 0.0
    auc_roc: float = 0.0
    discriminator_score: float = 0.5
    feature_importance: Dict[str, float] = field(default_factory=dict)
    loss_history: List[float] = field(default_factory=list)
    accuracy_history: List[float] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Metrik nesnesini JSON serileştirilebilir sözlüğe çevirir."""
        return asdict(self)


@dataclass
class StatisticalTestResult:
    """
    Tek bir istatistiksel test sonucunu temsil eder.

    Alanlar:
        test_name : Testin adı
        column    : Sınanan sütun adı
        statistic : Test istatistiği değeri
        p_value   : p-değeri
        passed    : Testin geçip geçmediği (p > eşik)
        threshold : Karar eşiği (varsayılan 0.05)
        details   : Ek bilgiler
    """

    test_name: str
    column: str
    statistic: float
    p_value: float
    passed: bool
    threshold: float = 0.05
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Sonucu JSON serileştirilebilir sözlüğe çevirir."""
        return asdict(self)


# ===========================================================================
# SimpleNeuralNetwork
# ===========================================================================

class SimpleNeuralNetwork:
    """
    Saf NumPy tabanlı tam bağlantılı sinir ağı.

    Bu sınıf, GAN discriminator'ı için gerekli tüm sinir ağı operasyonlarını
    (ileri yayılım, geri yayılım, ikili çapraz-entropi kaybı) sağlar.
    PyTorch veya TensorFlow kullanılmaz; yalnızca NumPy ile uygulanmıştır.

    Parametreler:
        layer_dims   : Her katmanın boyutunu listeleyen dizi
                       Örnek: [input_dim, 128, 64, 1]
        activations  : Her katman için aktivasyon fonksiyonu listesi
                       'relu', 'sigmoid', 'tanh', 'linear' desteklenir
        learning_rate: Gradient descent öğrenme oranı
        l2_lambda    : L2 düzenlileştirme katsayısı

    Örnek:
        >>> net = SimpleNeuralNetwork([10, 64, 32, 1], ['relu', 'relu', 'sigmoid'])
        >>> output = net.forward(X_batch)
        >>> loss = net.bce_loss(output, y_batch)
        >>> net.backward(output, y_batch, X_batch)
    """

    def __init__(
        self,
        layer_dims: List[int],
        activations: Optional[List[str]] = None,
        learning_rate: float = 0.001,
        l2_lambda: float = 1e-4,
    ):
        """
        Sinir ağını başlatır; ağırlıkları He başlatma ile oluşturur.

        Parametreler:
            layer_dims   : [giriş_boyutu, gizli1, gizli2, ..., çıkış_boyutu]
            activations  : Her katman çıkışı için aktivasyon adı listesi
            learning_rate: Öğrenme oranı
            l2_lambda    : L2 düzenlileştirme katsayısı
        """
        if len(layer_dims) < 2:
            raise ValueError("En az 2 katman boyutu gereklidir (giriş + çıkış).")

        self.layer_dims = layer_dims
        self.learning_rate = learning_rate
        self.l2_lambda = l2_lambda
        self.n_layers = len(layer_dims) - 1  # Ağırlık matrisi sayısı

        # Varsayılan aktivasyonlar: gizli katmanlar relu, çıkış sigmoid
        if activations is None:
            activations = ['relu'] * (self.n_layers - 1) + ['sigmoid']
        if len(activations) != self.n_layers:
            raise ValueError(
                f"Aktivasyon sayısı ({len(activations)}) katman sayısıyla "
                f"({self.n_layers}) eşleşmelidir."
            )
        self.activations = activations

        # Ağırlık matrisleri ve bias vektörleri (He başlatma)
        self.weights: List[np.ndarray] = []
        self.biases: List[np.ndarray] = []

        for i in range(self.n_layers):
            fan_in = layer_dims[i]
            fan_out = layer_dims[i + 1]
            # He başlatma: std = sqrt(2 / fan_in)
            scale = np.sqrt(2.0 / (fan_in + _EPS))
            W = np.random.randn(fan_in, fan_out) * scale
            b = np.zeros((1, fan_out))
            self.weights.append(W)
            self.biases.append(b)

        # İleri yayılım önbelleği (geri yayılım için)
        self._cache: Dict[str, Any] = {}

    # ------------------------------------------------------------------
    # Aktivasyon Fonksiyonları
    # ------------------------------------------------------------------

    @staticmethod
    def _sigmoid(z: np.ndarray) -> np.ndarray:
        """
        Sayısal olarak kararlı sigmoid aktivasyonu.

        Parametreler:
            z: Doğrusal kombinasyon çıktısı

        Döner:
            Sigmoid değerleri (0-1 arasında)
        """
        # Taşmayı önlemek için clip uygula
        z_clipped = np.clip(z, -500, 500)
        return 1.0 / (1.0 + np.exp(-z_clipped))

    @staticmethod
    def _relu(z: np.ndarray) -> np.ndarray:
        """
        ReLU aktivasyonu: max(0, z).

        Parametreler:
            z: Doğrusal kombinasyon çıktısı

        Döner:
            ReLU aktivasyonu uygulanmış değerler
        """
        return np.maximum(0.0, z)

    @staticmethod
    def _tanh(z: np.ndarray) -> np.ndarray:
        """
        Hiperbolik tanjant aktivasyonu.

        Parametreler:
            z: Doğrusal kombinasyon çıktısı

        Döner:
            tanh değerleri (-1 ile 1 arasında)
        """
        return np.tanh(z)

    def _activate(self, z: np.ndarray, name: str) -> np.ndarray:
        """
        İsme göre aktivasyon fonksiyonunu uygular.

        Parametreler:
            z   : Doğrusal çıktı
            name: 'relu', 'sigmoid', 'tanh', 'linear'

        Döner:
            Aktivasyon uygulanmış değerler

        Kaldırır:
            ValueError: Bilinmeyen aktivasyon adı verilirse
        """
        if name == 'relu':
            return self._relu(z)
        elif name == 'sigmoid':
            return self._sigmoid(z)
        elif name == 'tanh':
            return self._tanh(z)
        elif name == 'linear':
            return z
        else:
            raise ValueError(f"Bilinmeyen aktivasyon: {name}")

    def _activation_derivative(self, a: np.ndarray, z: np.ndarray, name: str) -> np.ndarray:
        """
        Aktivasyon fonksiyonunun türevini hesaplar.

        Parametreler:
            a   : Aktivasyon çıktısı (sigmoid/tanh için kullanışlı)
            z   : Pre-aktivasyon değeri (relu için)
            name: Aktivasyon fonksiyonu adı

        Döner:
            Türev değerleri (aynı şekil)
        """
        if name == 'relu':
            return (z > 0).astype(float)
        elif name == 'sigmoid':
            return a * (1.0 - a)
        elif name == 'tanh':
            return 1.0 - a ** 2
        elif name == 'linear':
            return np.ones_like(z)
        else:
            raise ValueError(f"Bilinmeyen aktivasyon türevi: {name}")

    # ------------------------------------------------------------------
    # İleri Yayılım
    # ------------------------------------------------------------------

    def forward(self, X: np.ndarray) -> np.ndarray:
        """
        İleri yayılım: Girişten çıkışa hesaplama.

        Geri yayılım için ara değerler (_cache) kaydedilir.

        Parametreler:
            X: Giriş matrisi şekli (batch_size, input_dim)

        Döner:
            Çıkış matrisi şekli (batch_size, output_dim)
        """
        self._cache['inputs'] = []    # Her katmanın girdisi
        self._cache['pre_acts'] = []  # Her katmanın pre-aktivasyon değeri
        self._cache['acts'] = []      # Her katmanın aktivasyon değeri

        current = X
        for i in range(self.n_layers):
            self._cache['inputs'].append(current)
            z = np.dot(current, self.weights[i]) + self.biases[i]
            a = self._activate(z, self.activations[i])
            self._cache['pre_acts'].append(z)
            self._cache['acts'].append(a)
            current = a

        return current  # Son katmanın çıktısı

    # ------------------------------------------------------------------
    # Kayıp Fonksiyonu
    # ------------------------------------------------------------------

    def bce_loss(self, y_pred: np.ndarray, y_true: np.ndarray) -> float:
        """
        İkili Çapraz-Entropi (Binary Cross-Entropy) kaybını hesaplar.

        L = -mean(y * log(ŷ) + (1 - y) * log(1 - ŷ))

        Parametreler:
            y_pred: Model tahminleri, şekil (batch_size, 1) veya (batch_size,)
            y_true: Gerçek etiketler (0 veya 1)

        Döner:
            Skalar kayıp değeri
        """
        y_pred = y_pred.reshape(-1)
        y_true = y_true.reshape(-1)
        # Sayısal kararlılık için clip
        y_pred_clipped = np.clip(y_pred, _EPS, 1.0 - _EPS)
        loss = -np.mean(
            y_true * np.log(y_pred_clipped) +
            (1.0 - y_true) * np.log(1.0 - y_pred_clipped)
        )
        return float(loss)

    # ------------------------------------------------------------------
    # Geri Yayılım (Backpropagation)
    # ------------------------------------------------------------------

    def backward(
        self,
        y_pred: np.ndarray,
        y_true: np.ndarray,
        X: np.ndarray
    ) -> None:
        """
        Geri yayılım ile ağırlıkları günceller (gradient descent).

        BCE kaybının gradyanı hesaplanır, her katmana zincir kuralıyla
        aktarılır ve ağırlıklar güncellenir.

        Parametreler:
            y_pred: İleri yayılım tahminleri
            y_true: Gerçek etiketler
            X     : Orijinal giriş verisi (cache'deki inputs[0] ile aynı)

        Notlar:
            - L2 düzenlileştirme ağırlık güncellemesine eklenir.
            - forward() çağrılmadan önce bu metot çağrılmamalıdır.
        """
        batch_size = y_pred.shape[0]

        # Çıkış katmanı gradyanı: dL/dŷ için türev
        y_pred_clipped = np.clip(y_pred.reshape(-1, 1), _EPS, 1.0 - _EPS)
        y_true_reshaped = y_true.reshape(-1, 1)

        # BCE kaybının sigmoid çıkışına göre türevi basitleşir: (ŷ - y) / batch
        delta = (y_pred_clipped - y_true_reshaped) / batch_size

        # Geri yayılım: son katmandan ilk katmana
        for i in reversed(range(self.n_layers)):
            layer_input = self._cache['inputs'][i]
            z_i = self._cache['pre_acts'][i]
            a_i = self._cache['acts'][i]

            # Aktivasyon türevi (çıkış katmanı sigmoid için sigmoid türevi)
            if i < self.n_layers - 1:
                # Ara katman: aktivasyon türevini uygula
                act_deriv = self._activation_derivative(a_i, z_i, self.activations[i])
                delta = delta * act_deriv

            # Ağırlık ve bias gradyanları
            dW = np.dot(layer_input.T, delta)
            db = np.sum(delta, axis=0, keepdims=True)

            # Gradient'i bir önceki katmana aktar
            if i > 0:
                delta = np.dot(delta, self.weights[i].T)

            # L2 düzenlileştirme
            dW += self.l2_lambda * self.weights[i]

            # Ağırlık güncellemesi (gradient descent)
            self.weights[i] -= self.learning_rate * dW
            self.biases[i] -= self.learning_rate * db

    # ------------------------------------------------------------------
    # Yardımcı Metotlar
    # ------------------------------------------------------------------

    def predict(self, X: np.ndarray) -> np.ndarray:
        """
        Veri için olasılık tahminleri üretir (eğitim önbelleği olmadan).

        Parametreler:
            X: Giriş verisi, şekil (n_samples, input_dim)

        Döner:
            Olasılık dizisi, şekil (n_samples,)
        """
        # Önbelleği geçici olarak baskıla (çıkarım modunda)
        current = X
        for i in range(self.n_layers):
            z = np.dot(current, self.weights[i]) + self.biases[i]
            current = self._activate(z, self.activations[i])
        return current.flatten()

    def get_layer_count(self) -> int:
        """Ağdaki katman sayısını döner."""
        return self.n_layers

    def get_parameter_count(self) -> int:
        """Toplam eğitilebilir parametre sayısını döner."""
        total = 0
        for W, b in zip(self.weights, self.biases):
            total += W.size + b.size
        return total

    def __repr__(self) -> str:
        dims = " -> ".join(str(d) for d in self.layer_dims)
        return (
            f"SimpleNeuralNetwork(dims=[{dims}], "
            f"lr={self.learning_rate}, params={self.get_parameter_count()})"
        )


# ===========================================================================
# GANDiscriminator
# ===========================================================================

class GANDiscriminator:
    """
    GAN Discriminator: Gerçek ve sentetik verileri ayırt eden sinir ağı.

    Bu sınıf, pandas DataFrame formatındaki gerçek ve sentetik bankacılık
    verilerini karşılaştırmak için tam bir eğitim ve değerlendirme döngüsü
    sağlar. Kategorik değişkenler otomatik olarak kodlanır, sayısal değişkenler
    normalleştirilir.

    Parametreler:
        hidden_layers: Gizli katman nöron sayıları listesi, varsayılan [128, 64, 32]
        learning_rate: Öğrenme oranı, varsayılan 0.001
        epochs       : Eğitim epok sayısı, varsayılan 100
        batch_size   : Batch boyutu, varsayılan 32

    Özellikler:
        - _prepare_data()        : Normalizasyon ve kategorik kodlama
        - train()                : Tam eğitim döngüsü
        - evaluate()             : DiscriminatorMetrics döner
        - feature_importance()   : Permütasyon tabanlı özellik önemi
        - predict_proba()        : Gerçek olma olasılığı
        - get_discriminator_score: 0-1 kalite puanı (0.5 = mükemmel sentez)

    Örnek:
        >>> disc = GANDiscriminator(hidden_layers=[64, 32], epochs=50)
        >>> disc.train(real_df, synthetic_df)
        >>> metrics = disc.evaluate(synthetic_df)
        >>> score = disc.get_discriminator_score(synthetic_df)
        >>> print(f"Discriminator Puanı: {score:.4f}")
    """

    def __init__(
        self,
        hidden_layers: List[int] = None,
        learning_rate: float = 0.001,
        epochs: int = 100,
        batch_size: int = 32,
    ):
        """
        GANDiscriminator'ı başlatır.

        Parametreler:
            hidden_layers: Gizli katman boyutları (varsayılan [128, 64, 32])
            learning_rate: Öğrenme oranı
            epochs       : Maksimum eğitim epok sayısı
            batch_size   : Mini-batch boyutu
        """
        self.hidden_layers = hidden_layers if hidden_layers is not None else [128, 64, 32]
        self.learning_rate = learning_rate
        self.epochs = epochs
        self.batch_size = batch_size

        # Durum değişkenleri
        self.is_trained: bool = False
        self.network: Optional[SimpleNeuralNetwork] = None
        self.feature_names: List[str] = []
        self.n_features: int = 0

        # Veri ön işleme bilgileri
        self._num_cols: List[str] = []
        self._cat_cols: List[str] = []
        self._num_stats: Dict[str, Tuple[float, float]] = {}  # (mean, std)
        self._cat_encodings: Dict[str, Dict[Any, int]] = {}   # col -> {val -> idx}

        # Eğitim geçmişi ve önbellekler
        self._train_history: Dict[str, List[float]] = {'loss': [], 'accuracy': []}
        self._feature_importance_cache: Dict[str, float] = {}

        logger.info(
            f"GANDiscriminator oluşturuldu: gizli_katmanlar={self.hidden_layers}, "
            f"lr={learning_rate}, epochs={epochs}, batch={batch_size}"
        )

    # ------------------------------------------------------------------
    # Veri Ön İşleme
    # ------------------------------------------------------------------

    def _prepare_data(
        self,
        df: pd.DataFrame,
        fit: bool = False
    ) -> np.ndarray:
        """
        DataFrame'i sinir ağı için uygun NumPy dizisine dönüştürür.

        Sayısal sütunlar z-skor normalizasyonu ile ölçeklenir.
        Kategorik sütunlar tam sayı kodlamasıyla dönüştürülür.
        NaN değerleri sütun ortalaması veya 0 ile doldurulur.

        Parametreler:
            df : Giriş DataFrame'i
            fit: True ise normalizasyon istatistikleri ve kodlamalar öğrenilir;
                 False ise önceden öğrenilen değerler kullanılır.

        Döner:
            NumPy dizisi, şekil (n_samples, n_features)

        Kaldırır:
            ValueError: fit=False iken _prepare_data hiç çağrılmamışsa
        """
        processed_cols = []

        if fit:
            self._num_cols = []
            self._cat_cols = []
            self._num_stats = {}
            self._cat_encodings = {}

            for col in df.columns:
                if pd.api.types.is_numeric_dtype(df[col]):
                    self._num_cols.append(col)
                else:
                    self._cat_cols.append(col)

        # Sayısal sütunları işle
        for col in self._num_cols:
            if col not in df.columns:
                # Eksik sütun: sıfır doldur
                processed_cols.append(np.zeros(len(df)))
                continue

            vals = df[col].values.astype(float)
            # NaN doldurma
            nan_mask = np.isnan(vals)
            if np.any(nan_mask):
                col_mean = np.nanmean(vals) if not np.all(nan_mask) else 0.0
                vals[nan_mask] = col_mean

            if fit:
                mean = float(np.mean(vals))
                std = float(np.std(vals))
                self._num_stats[col] = (mean, std)
            else:
                mean, std = self._num_stats.get(col, (0.0, 1.0))

            # Z-skor normalizasyonu
            if std > _EPS:
                vals = (vals - mean) / std
            else:
                vals = vals - mean  # Sabit sütun

            # Uç değerleri kırp
            vals = np.clip(vals, -10.0, 10.0)
            processed_cols.append(vals)

        # Kategorik sütunları işle
        for col in self._cat_cols:
            if col not in df.columns:
                processed_cols.append(np.zeros(len(df)))
                continue

            vals = df[col].astype(str).values

            if fit:
                unique_vals = sorted(set(vals))
                self._cat_encodings[col] = {v: i for i, v in enumerate(unique_vals)}

            encoding = self._cat_encodings.get(col, {})
            # Bilinmeyen kategoriler için -1, sonra normalize et
            encoded = np.array([encoding.get(v, -1) for v in vals], dtype=float)
            n_cats = max(len(encoding), 1)
            # [0, 1] aralığına normalize et
            encoded = (encoded + 1.0) / (n_cats + 1.0)
            processed_cols.append(encoded)

        if not processed_cols:
            raise ValueError("İşlenecek sütun bulunamadı.")

        # Sütunları birleştir
        result = np.column_stack(processed_cols)

        if fit:
            self.feature_names = self._num_cols + self._cat_cols
            self.n_features = result.shape[1]

        return result

    # ------------------------------------------------------------------
    # Eğitim
    # ------------------------------------------------------------------

    def train(
        self,
        real_data: pd.DataFrame,
        synthetic_data: pd.DataFrame,
    ) -> Dict[str, List[float]]:
        """
        Discriminator'ı gerçek ve sentetik veriler üzerinde eğitir.

        Gerçek örnekler 1, sentetik örnekler 0 olarak etiketlenir.
        Eğitim seti karıştırılır ve mini-batch gradient descent kullanılır.

        Parametreler:
            real_data     : Gerçek bankacılık verisi (pd.DataFrame)
            synthetic_data: Sentetik olarak üretilmiş veri (pd.DataFrame)

        Döner:
            Eğitim geçmişi: {'loss': [...], 'accuracy': [...]}

        Kaldırır:
            ValueError: Veri boşsa veya DataFrame değilse
        """
        if not isinstance(real_data, pd.DataFrame):
            raise ValueError("real_data bir pandas DataFrame olmalıdır.")
        if not isinstance(synthetic_data, pd.DataFrame):
            raise ValueError("synthetic_data bir pandas DataFrame olmalıdır.")
        if len(real_data) == 0 or len(synthetic_data) == 0:
            raise ValueError("Eğitim verisi boş olamaz.")

        logger.info(
            f"Discriminator eğitimi başlıyor: "
            f"gerçek={len(real_data)}, sentetik={len(synthetic_data)}"
        )

        # Veri hazırlama (fit=True: normalizasyon parametrelerini öğren)
        X_real = self._prepare_data(real_data, fit=True)
        X_syn = self._prepare_data(synthetic_data, fit=False)

        # Etiket oluşturma: gerçek=1, sentetik=0
        y_real = np.ones(len(X_real))
        y_syn = np.zeros(len(X_syn))

        # Veriyi birleştir
        X_all = np.vstack([X_real, X_syn])
        y_all = np.hstack([y_real, y_syn])

        # Sinir ağı mimarisi oluştur
        layer_dims = [self.n_features] + self.hidden_layers + [1]
        activations = ['relu'] * len(self.hidden_layers) + ['sigmoid']

        self.network = SimpleNeuralNetwork(
            layer_dims=layer_dims,
            activations=activations,
            learning_rate=self.learning_rate,
        )

        logger.info(
            f"Ağ mimarisi: {self.network} | Toplam parametre: {self.network.get_parameter_count()}"
        )

        # Eğitim döngüsü
        history: Dict[str, List[float]] = {'loss': [], 'accuracy': []}
        n_samples = len(X_all)

        for epoch in range(self.epochs):
            # Her epokta veriyi karıştır
            shuffle_idx = np.random.permutation(n_samples)
            X_shuffled = X_all[shuffle_idx]
            y_shuffled = y_all[shuffle_idx]

            epoch_losses: List[float] = []
            epoch_accs: List[float] = []

            # Mini-batch döngüsü
            for start in range(0, n_samples, self.batch_size):
                end = min(start + self.batch_size, n_samples)
                X_batch = X_shuffled[start:end]
                y_batch = y_shuffled[start:end]

                # İleri yayılım
                y_pred = self.network.forward(X_batch)

                # Kayıp hesapla
                loss = self.network.bce_loss(y_pred, y_batch)
                epoch_losses.append(loss)

                # Doğruluk hesapla
                pred_labels = (y_pred > 0.5).astype(float)
                acc = float(np.mean(pred_labels == y_batch))
                epoch_accs.append(acc)

                # Geri yayılım
                self.network.backward(y_pred, y_batch, X_batch)

            # Epok ortalamaları kaydet
            epoch_loss = float(np.mean(epoch_losses))
            epoch_acc = float(np.mean(epoch_accs))
            history['loss'].append(epoch_loss)
            history['accuracy'].append(epoch_acc)

            # Her 10 epokta bir günlük yaz
            if (epoch + 1) % 10 == 0 or epoch == 0:
                logger.info(
                    f"Epok {epoch + 1:4d}/{self.epochs} | "
                    f"Kayıp: {epoch_loss:.4f} | "
                    f"Doğruluk: {epoch_acc:.4f}"
                )

            # Erken durdurma: kayıp yeterince küçükse dur
            if epoch_loss < 0.01 and epoch_acc > 0.99:
                logger.info(f"Erken durdurma: epok {epoch + 1}, kayıp={epoch_loss:.4f}")
                break

        self._train_history = history
        self.is_trained = True
        logger.info("Discriminator eğitimi tamamlandı.")
        return history

    # ------------------------------------------------------------------
    # Değerlendirme
    # ------------------------------------------------------------------

    def evaluate(
        self,
        data: pd.DataFrame,
        labels: Optional[np.ndarray] = None
    ) -> DiscriminatorMetrics:
        """
        Veri üzerinde discriminator performansını değerlendirir.

        Etiket verilmezse tüm veri sentetik varsayılır (label=0).

        Parametreler:
            data  : Değerlendirilecek veri (pd.DataFrame)
            labels: İsteğe bağlı gerçek etiketler (0/1 dizisi)

        Döner:
            DiscriminatorMetrics nesnesi

        Kaldırır:
            RuntimeError: Model henüz eğitilmemişse
        """
        self._check_trained()

        X = self._prepare_data(data, fit=False)
        y_pred = self.network.predict(X)

        if labels is None:
            # Sentetik veri değerlendirmesi: tüm etiketler 0
            labels = np.zeros(len(X))

        labels = labels.astype(float)
        pred_binary = (y_pred > 0.5).astype(float)

        # Temel metrikler
        accuracy = float(np.mean(pred_binary == labels))

        # TP, FP, FN hesapla
        tp = float(np.sum((pred_binary == 1) & (labels == 1)))
        fp = float(np.sum((pred_binary == 1) & (labels == 0)))
        fn = float(np.sum((pred_binary == 0) & (labels == 1)))

        precision = tp / (tp + fp + _EPS)
        recall = tp / (tp + fn + _EPS)
        f1 = 2 * precision * recall / (precision + recall + _EPS)

        # AUC-ROC yaklaşımı (trapez yöntemi)
        auc_roc = self._compute_auc_roc(y_pred, labels)

        # Discriminator puanı: 0.5 = mükemmel sentez (ayırt edilemez)
        disc_score = self.get_discriminator_score(data)

        # Özellik önemi
        feat_imp = self.feature_importance(data)

        return DiscriminatorMetrics(
            accuracy=accuracy,
            precision=precision,
            recall=recall,
            f1_score=f1,
            auc_roc=auc_roc,
            discriminator_score=disc_score,
            feature_importance=feat_imp,
            loss_history=self._train_history.get('loss', []),
            accuracy_history=self._train_history.get('accuracy', []),
        )

    @staticmethod
    def _compute_auc_roc(
        y_score: np.ndarray,
        y_true: np.ndarray
    ) -> float:
        """
        Trapez yöntemiyle AUC-ROC alanını hesaplar.

        Parametreler:
            y_score: Model olasılık çıktısı
            y_true : Gerçek ikili etiketler (0/1)

        Döner:
            AUC-ROC değeri (0-1 arasında)
        """
        if len(np.unique(y_true)) < 2:
            # Tek sınıf: anlamsız AUC
            return 0.5

        # Eşikleri azalan sırayla sırala
        thresholds = np.sort(np.unique(y_score))[::-1]
        tprs = [0.0]
        fprs = [0.0]

        n_pos = float(np.sum(y_true == 1))
        n_neg = float(np.sum(y_true == 0))

        if n_pos == 0 or n_neg == 0:
            return 0.5

        for thresh in thresholds:
            pred = (y_score >= thresh).astype(float)
            tp = float(np.sum((pred == 1) & (y_true == 1)))
            fp = float(np.sum((pred == 1) & (y_true == 0)))
            tprs.append(tp / n_pos)
            fprs.append(fp / n_neg)

        tprs.append(1.0)
        fprs.append(1.0)

        # Trapez integrasyonu
        auc = float(np.trapz(tprs, fprs))
        return abs(auc)

    # ------------------------------------------------------------------
    # Özellik Önemi
    # ------------------------------------------------------------------

    def feature_importance(
        self,
        data: pd.DataFrame,
        n_repeats: int = 10
    ) -> Dict[str, float]:
        """
        Permütasyon tabanlı özellik önemini hesaplar.

        Her sütun sırayla karıştırılır ve doğruluk düşüşü ölçülür.
        Daha büyük düşüş = daha önemli özellik.

        Parametreler:
            data     : Değerlendirilecek veri (pd.DataFrame)
            n_repeats: Her özellik için permütasyon sayısı

        Döner:
            Normalize edilmiş özellik önemi sözlüğü {sütun_adı: önem_puanı}

        Kaldırır:
            RuntimeError: Model henüz eğitilmemişse
        """
        self._check_trained()

        X = self._prepare_data(data, fit=False)
        baseline_preds = self.network.predict(X)
        baseline_acc = float(np.mean(baseline_preds))

        importance_raw: Dict[str, float] = {}

        for feat_idx, feat_name in enumerate(self.feature_names):
            drops = []
            for _ in range(n_repeats):
                X_perm = X.copy()
                # Sütunu karıştır
                X_perm[:, feat_idx] = np.random.permutation(X_perm[:, feat_idx])
                perm_preds = self.network.predict(X_perm)
                perm_acc = float(np.mean(perm_preds))
                drops.append(abs(baseline_acc - perm_acc))
            importance_raw[feat_name] = float(np.mean(drops))

        # Normalize et (toplam 1)
        total_imp = sum(importance_raw.values()) + _EPS
        importance_normalized = {k: v / total_imp for k, v in importance_raw.items()}

        # Azalan sırayla sırala
        importance_sorted = dict(
            sorted(importance_normalized.items(), key=lambda x: x[1], reverse=True)
        )

        self._feature_importance_cache = importance_sorted
        return importance_sorted

    # ------------------------------------------------------------------
    # Tahmin Metotları
    # ------------------------------------------------------------------

    def predict_proba(self, data: pd.DataFrame) -> np.ndarray:
        """
        Her örnek için gerçek olma olasılığını döner.

        Yüksek olasılık (> 0.5) örneklerinin gerçek olduğunu,
        düşük olasılık (< 0.5) sentetik olduğunu gösterir.

        Parametreler:
            data: Tahmin edilecek veri (pd.DataFrame)

        Döner:
            Olasılık dizisi, şekil (n_samples,), değerler [0, 1]

        Kaldırır:
            RuntimeError: Model henüz eğitilmemişse
        """
        self._check_trained()
        X = self._prepare_data(data, fit=False)
        return self.network.predict(X)

    def get_discriminator_score(self, data: pd.DataFrame) -> float:
        """
        Veri kümesi için tek bir discriminator kalite puanı döner.

        Puan yorumu:
            0.5 → Mükemmel sentez (model gerçek/sentetik ayırt edemiyor)
            1.0 → Tüm örnekler gerçek olarak sınıflandırıldı
            0.0 → Tüm örnekler sentetik olarak sınıflandırıldı

        Formül: score = 1 - |mean(pred) - 0.5| * 2

        Parametreler:
            data: Puanlanacak veri (pd.DataFrame)

        Döner:
            Kalite puanı [0, 1] aralığında; 0.5 en iyidir.

        Kaldırır:
            RuntimeError: Model henüz eğitilmemişse
        """
        self._check_trained()
        proba = self.predict_proba(data)
        mean_proba = float(np.mean(proba))
        # 0.5'ten sapma: ne kadar yakınsa o kadar iyi sentez
        score = 1.0 - abs(mean_proba - 0.5) * 2.0
        return float(np.clip(score, 0.0, 1.0))

    # ------------------------------------------------------------------
    # Yardımcı Metotlar
    # ------------------------------------------------------------------

    def _check_trained(self) -> None:
        """Model eğitilmemişse RuntimeError fırlatır."""
        if not self.is_trained or self.network is None:
            raise RuntimeError(
                "Discriminator henüz eğitilmedi. Önce train() metodunu çağırın."
            )

    def get_training_history(self) -> Dict[str, List[float]]:
        """Eğitim kayıp ve doğruluk geçmişini döner."""
        return self._train_history.copy()

    def get_feature_names(self) -> List[str]:
        """İşlenmiş özellik adlarını döner."""
        return self.feature_names.copy()

    def __repr__(self) -> str:
        status = "eğitildi" if self.is_trained else "eğitilmedi"
        return (
            f"GANDiscriminator(hidden={self.hidden_layers}, "
            f"lr={self.learning_rate}, epochs={self.epochs}, durum={status})"
        )


# ===========================================================================
# StatisticalValidator
# ===========================================================================

class StatisticalValidator:
    """
    Gerçek ve sentetik veri arasındaki istatistiksel benzerliği ölçer.

    Saf NumPy ile uygulanan istatistiksel testler:
        - Kolmogorov-Smirnov (KS) testi: Dağılım benzerliği
        - Ki-kare testi: Kategorik değişken frekans benzerliği
        - Korelasyon benzerliği: Frobenius norm ile matris karşılaştırması
        - Wasserstein mesafesi: Earth Mover's Distance yaklaşımı

    Örnek:
        >>> validator = StatisticalValidator()
        >>> results = validator.run_all_tests(real_df, synthetic_df)
        >>> for col, res in results['ks_test'].items():
        ...     print(f"{col}: p={res['p_value']:.4f}")
    """

    def __init__(self, significance_level: float = 0.05):
        """
        StatisticalValidator'ı başlatır.

        Parametreler:
            significance_level: İstatistiksel anlamlılık eşiği (varsayılan 0.05)
        """
        self.significance_level = significance_level
        logger.debug(f"StatisticalValidator başlatıldı (alpha={significance_level})")

    # ------------------------------------------------------------------
    # Kolmogorov-Smirnov Testi
    # ------------------------------------------------------------------

    def ks_test(
        self,
        real: pd.Series,
        synthetic: pd.Series
    ) -> StatisticalTestResult:
        """
        İki seri arasında Kolmogorov-Smirnov testini uygular.

        KS istatistiği, iki kümülatif dağılım fonksiyonu arasındaki
        maksimum mutlak farkı ölçer.

        Parametreler:
            real     : Gerçek veri serisi (sayısal)
            synthetic: Sentetik veri serisi (sayısal)

        Döner:
            StatisticalTestResult nesnesi (KS istatistiği ve p-değeriyle)
        """
        col_name = real.name if real.name else "bilinmeyen"

        # NaN temizleme
        r = real.dropna().values.astype(float)
        s = synthetic.dropna().values.astype(float)

        if len(r) == 0 or len(s) == 0:
            return StatisticalTestResult(
                test_name="ks_test",
                column=col_name,
                statistic=1.0,
                p_value=0.0,
                passed=False,
                threshold=self.significance_level,
                details={"hata": "Boş veri serisi"}
            )

        # KS istatistiğini saf NumPy ile hesapla
        ks_stat, p_value = self._ks_statistic(r, s)

        return StatisticalTestResult(
            test_name="ks_test",
            column=col_name,
            statistic=float(ks_stat),
            p_value=float(p_value),
            passed=p_value >= self.significance_level,
            threshold=self.significance_level,
            details={
                "n_real": len(r),
                "n_synthetic": len(s),
                "real_mean": float(np.mean(r)),
                "synthetic_mean": float(np.mean(s)),
                "real_std": float(np.std(r)),
                "synthetic_std": float(np.std(s)),
            }
        )

    @staticmethod
    def _ks_statistic(
        x: np.ndarray,
        y: np.ndarray
    ) -> Tuple[float, float]:
        """
        İki dizi arasında KS istatistiği ve p-değerini hesaplar.

        Parametreler:
            x: Birinci örnek dizisi
            y: İkinci örnek dizisi

        Döner:
            (ks_stat, p_value) demeti
        """
        # Tüm gözlemler sıralanmış
        all_vals = np.sort(np.concatenate([x, y]))
        n1 = len(x)
        n2 = len(y)

        # ECDF değerleri
        ecdf1 = np.searchsorted(np.sort(x), all_vals, side='right') / n1
        ecdf2 = np.searchsorted(np.sort(y), all_vals, side='right') / n2

        # Maksimum mutlak fark
        ks_stat = float(np.max(np.abs(ecdf1 - ecdf2)))

        # Asimptotik p-değeri (Kolmogorov dağılımı)
        n = n1 * n2 / (n1 + n2)
        z = ks_stat * np.sqrt(n)

        # Kolmogorov-Smirnov sonsuz serisi yaklaşımı
        if z < 0.27:
            p_value = 1.0
        elif z < 1.0:
            p_value = float(
                1.0 - np.sqrt(2 * np.pi) / z * np.sum(
                    [np.exp(-((2 * k - 1) ** 2) * np.pi ** 2 / (8 * z ** 2))
                     for k in range(1, 20)]
                )
            )
        else:
            # Büyük z için yaklaşım
            p_value = float(
                2.0 * np.sum(
                    [(-1) ** (k - 1) * np.exp(-2 * k ** 2 * z ** 2)
                     for k in range(1, 20)]
                )
            )

        p_value = float(np.clip(p_value, 0.0, 1.0))
        return ks_stat, p_value

    # ------------------------------------------------------------------
    # Ki-Kare Testi
    # ------------------------------------------------------------------

    def chi_square_test(
        self,
        real: pd.Series,
        synthetic: pd.Series
    ) -> StatisticalTestResult:
        """
        Kategorik değişkenler için Ki-kare uyum testi uygular.

        Gerçek veri frekans dağılımının referans olduğu, sentetik verinin
        buna ne kadar uyduğunu ölçer.

        Parametreler:
            real     : Gerçek kategorik seri
            synthetic: Sentetik kategorik seri

        Döner:
            StatisticalTestResult nesnesi (Ki-kare istatistiği ve p-değeriyle)
        """
        col_name = real.name if real.name else "bilinmeyen"

        # Frekans sayım
        real_counts = real.value_counts()
        syn_counts = synthetic.value_counts()

        # Tüm kategorileri birleştir
        all_cats = sorted(set(real_counts.index) | set(syn_counts.index))

        if len(all_cats) < 2:
            return StatisticalTestResult(
                test_name="chi_square_test",
                column=col_name,
                statistic=0.0,
                p_value=1.0,
                passed=True,
                threshold=self.significance_level,
                details={"uyari": "Tek kategorili sütun"}
            )

        # Gözlenen ve beklenen frekanslar
        observed = np.array([syn_counts.get(c, 0) for c in all_cats], dtype=float)
        expected_raw = np.array([real_counts.get(c, 0) for c in all_cats], dtype=float)

        # Sıfır frekansları düzelt (Laplace düzeltmesi)
        expected_raw += 1.0
        observed += 1.0

        # Sentetik toplamı gerçek toplamına ölçeklendir
        expected = expected_raw / expected_raw.sum() * observed.sum()

        # Ki-kare istatistiği
        chi2_stat = float(np.sum((observed - expected) ** 2 / (expected + _EPS)))

        # Serbestlik derecesi
        dof = len(all_cats) - 1

        # Ki-kare p-değeri (regularize edilmiş üst-gama fonksiyonu yaklaşımı)
        p_value = self._chi2_pvalue(chi2_stat, dof)

        return StatisticalTestResult(
            test_name="chi_square_test",
            column=col_name,
            statistic=chi2_stat,
            p_value=float(p_value),
            passed=p_value >= self.significance_level,
            threshold=self.significance_level,
            details={
                "dof": dof,
                "n_categories": len(all_cats),
                "categories": list(all_cats[:20]),  # İlk 20 kategori
            }
        )

    @staticmethod
    def _chi2_pvalue(chi2: float, dof: int) -> float:
        """
        Ki-kare p-değerini yaklaşık olarak hesaplar.

        Düşük serbestlik derecesi için normal yaklaşım kullanılır.

        Parametreler:
            chi2: Ki-kare istatistiği
            dof : Serbestlik derecesi

        Döner:
            p-değeri [0, 1] aralığında
        """
        if dof <= 0:
            return 1.0
        if chi2 <= 0:
            return 1.0

        # Wilson-Hilferty normal yaklaşımı
        k = float(dof)
        if k > 100:
            # Büyük dof için normal yaklaşım
            z = ((chi2 / k) ** (1.0 / 3.0) - (1.0 - 2.0 / (9.0 * k))) / np.sqrt(2.0 / (9.0 * k))
            p = 1.0 - 0.5 * (1.0 + np.sign(z) * float(np.sqrt(1.0 - np.exp(-2 * z ** 2 / np.pi))))
        else:
            # Gamma dağılımı CDF yaklaşımı (Poisson zinciri)
            # Basit Monte Carlo yaklaşımı (100 örnek)
            n_mc = 5000
            samples = np.sum(np.random.standard_normal((n_mc, dof)) ** 2, axis=1)
            p = float(np.mean(samples >= chi2))

        return float(np.clip(p, 0.0, 1.0))

    # ------------------------------------------------------------------
    # Korelasyon Benzerliği
    # ------------------------------------------------------------------

    def correlation_similarity(
        self,
        real: pd.DataFrame,
        synthetic: pd.DataFrame
    ) -> Dict[str, Any]:
        """
        İki DataFrame'in korelasyon matrislerini Frobenius normu ile karşılaştırır.

        Parametreler:
            real     : Gerçek veri DataFrame'i
            synthetic: Sentetik veri DataFrame'i

        Döner:
            Şu anahtarları içeren sözlük:
                'frobenius_distance': Frobenius normu mesafesi (düşük = benzer)
                'similarity_score'  : [0, 1] benzerlik puanı (1 = özdeş)
                'real_corr'         : Gerçek korelasyon matrisi
                'synthetic_corr'    : Sentetik korelasyon matrisi
                'column_differences': Sütun bazlı korelasyon farkları
        """
        # Yalnızca sayısal sütunlar
        num_cols = [c for c in real.columns if pd.api.types.is_numeric_dtype(real[c])]
        num_cols = [c for c in num_cols if c in synthetic.columns]

        if len(num_cols) < 2:
            return {
                "frobenius_distance": 0.0,
                "similarity_score": 1.0,
                "uyari": "Karşılaştırmak için en az 2 sayısal sütun gereklidir."
            }

        # NaN temizleme
        r = real[num_cols].fillna(real[num_cols].mean()).values.astype(float)
        s = synthetic[num_cols].fillna(synthetic[num_cols].mean()).values.astype(float)

        # Korelasyon matrisleri
        corr_real = np.corrcoef(r.T)
        corr_syn = np.corrcoef(s.T)

        # NaN kontrolü
        corr_real = np.nan_to_num(corr_real, nan=0.0)
        corr_syn = np.nan_to_num(corr_syn, nan=0.0)

        # Frobenius normu
        diff_matrix = corr_real - corr_syn
        frobenius = float(np.linalg.norm(diff_matrix, 'fro'))

        # Benzerlik puanı: normalleştirilmiş (max Frobenius = sqrt(2*n^2))
        max_possible = np.sqrt(2.0) * len(num_cols)
        similarity = float(np.clip(1.0 - frobenius / (max_possible + _EPS), 0.0, 1.0))

        # Sütun bazlı farklar
        col_diffs = {}
        for i, col in enumerate(num_cols):
            col_diff = float(np.mean(np.abs(corr_real[i] - corr_syn[i])))
            col_diffs[col] = col_diff

        return {
            "frobenius_distance": frobenius,
            "similarity_score": similarity,
            "real_corr": corr_real.tolist(),
            "synthetic_corr": corr_syn.tolist(),
            "column_differences": col_diffs,
            "columns": num_cols,
        }

    # ------------------------------------------------------------------
    # Wasserstein Mesafesi
    # ------------------------------------------------------------------

    def wasserstein_distance(
        self,
        real: pd.Series,
        synthetic: pd.Series
    ) -> Dict[str, Any]:
        """
        İki dağılım arasındaki Wasserstein-1 (Earth Mover's) mesafesini hesaplar.

        Sıralanmış diziler arasındaki mutlak farkların ortalaması olarak
        hesaplanır (1-boyutlu Wasserstein-1 için analitik çözüm).

        Parametreler:
            real     : Gerçek veri serisi (sayısal)
            synthetic: Sentetik veri serisi (sayısal)

        Döner:
            Şu anahtarları içeren sözlük:
                'distance'          : Wasserstein-1 mesafesi
                'normalized_distance': [0, 1] normalleştirilmiş mesafe
                'column'            : Sütun adı
        """
        col_name = real.name if real.name else "bilinmeyen"

        r = real.dropna().values.astype(float)
        s = synthetic.dropna().values.astype(float)

        if len(r) == 0 or len(s) == 0:
            return {
                "distance": float('inf'),
                "normalized_distance": 1.0,
                "column": col_name,
                "hata": "Boş veri serisi"
            }

        # Eşit sayıda örnek için yeniden örnekle
        n = max(len(r), len(s))
        r_sorted = np.sort(np.random.choice(r, size=n, replace=True))
        s_sorted = np.sort(np.random.choice(s, size=n, replace=True))

        # Wasserstein-1: sıralanmış ECDFler arasındaki L1 mesafesi
        distance = float(np.mean(np.abs(r_sorted - s_sorted)))

        # Normalize et (verinin ölçeğine göre)
        data_range = float(np.max(np.concatenate([r, s])) - np.min(np.concatenate([r, s])))
        normalized = distance / (data_range + _EPS)

        return {
            "distance": distance,
            "normalized_distance": float(np.clip(normalized, 0.0, 1.0)),
            "column": col_name,
            "n_samples": n,
        }

    # ------------------------------------------------------------------
    # Tüm Testleri Çalıştır
    # ------------------------------------------------------------------

    def run_all_tests(
        self,
        real: pd.DataFrame,
        synthetic: pd.DataFrame
    ) -> Dict[str, Any]:
        """
        Tüm istatistiksel testleri tek seferde çalıştırır.

        Parametreler:
            real     : Gerçek veri DataFrame'i
            synthetic: Sentetik veri DataFrame'i

        Döner:
            Şu anahtarları içeren kapsamlı sonuç sözlüğü:
                'ks_test'              : Sütun başına KS test sonuçları
                'chi_square_test'      : Kategorik sütunlar için Ki-kare sonuçları
                'correlation_similarity: Korelasyon matris karşılaştırması
                'wasserstein_distances': Sütun başına Wasserstein mesafeleri
                'summary'              : Genel geçme/başarısızlık özeti
                'overall_score'        : 0-1 genel kalite puanı
        """
        logger.info("Tüm istatistiksel testler çalıştırılıyor...")
        results: Dict[str, Any] = {}
        passed_tests = 0
        total_tests = 0

        # 1. KS testi (sayısal sütunlar)
        ks_results = {}
        for col in real.columns:
            if col in synthetic.columns and pd.api.types.is_numeric_dtype(real[col]):
                res = self.ks_test(real[col], synthetic[col])
                ks_results[col] = res.to_dict()
                total_tests += 1
                if res.passed:
                    passed_tests += 1
        results['ks_test'] = ks_results

        # 2. Ki-kare testi (kategorik sütunlar)
        chi_results = {}
        for col in real.columns:
            if col in synthetic.columns and not pd.api.types.is_numeric_dtype(real[col]):
                res = self.chi_square_test(real[col], synthetic[col])
                chi_results[col] = res.to_dict()
                total_tests += 1
                if res.passed:
                    passed_tests += 1
        results['chi_square_test'] = chi_results

        # 3. Korelasyon benzerliği
        corr_result = self.correlation_similarity(real, synthetic)
        results['correlation_similarity'] = corr_result

        # 4. Wasserstein mesafeleri (sayısal sütunlar)
        wass_results = {}
        for col in real.columns:
            if col in synthetic.columns and pd.api.types.is_numeric_dtype(real[col]):
                wass_results[col] = self.wasserstein_distance(real[col], synthetic[col])
        results['wasserstein_distances'] = wass_results

        # Özet
        pass_rate = passed_tests / max(total_tests, 1)
        corr_score = corr_result.get('similarity_score', 0.5)
        avg_wass = float(np.mean([
            v.get('normalized_distance', 0.5)
            for v in wass_results.values()
        ])) if wass_results else 0.5

        overall_score = 0.5 * pass_rate + 0.3 * corr_score + 0.2 * (1.0 - avg_wass)

        results['summary'] = {
            'total_tests': total_tests,
            'passed_tests': passed_tests,
            'failed_tests': total_tests - passed_tests,
            'pass_rate': float(pass_rate),
        }
        results['overall_score'] = float(np.clip(overall_score, 0.0, 1.0))

        logger.info(
            f"Testler tamamlandı: {passed_tests}/{total_tests} geçti "
            f"(genel puan: {overall_score:.4f})"
        )
        return results


# ===========================================================================
# DiscriminatorReport
# ===========================================================================

class DiscriminatorReport:
    """
    GAN discriminator değerlendirmesinin kapsamlı raporunu üretir.

    Bu sınıf, discriminator metrikleri, istatistiksel test sonuçları,
    özellik önemi ve genel kalite değerlendirmesini birleştirerek
    hem makine okunabilir (JSON) hem de insan okunabilir metin formatında
    raporlar oluşturur.

    Kullanım:
        >>> report = DiscriminatorReport.generate(discriminator, validator, real_df, syn_df)
        >>> print(report.summary_text())
        >>> report_dict = report.to_dict()
        >>> with open("report.json", "w") as f:
        ...     json.dump(report_dict, f, indent=2)
    """

    def __init__(self):
        """Boş bir DiscriminatorReport nesnesi oluşturur."""
        self._report: Dict[str, Any] = {}
        self._generated_at: Optional[str] = None

    @classmethod
    def generate(
        cls,
        discriminator: GANDiscriminator,
        validator: StatisticalValidator,
        real_data: pd.DataFrame,
        synthetic_data: pd.DataFrame,
    ) -> "DiscriminatorReport":
        """
        Discriminator ve validator kullanarak tam rapor üretir.

        Bu sınıf metodu, discriminator eğitildikten sonra kapsamlı
        bir kalite değerlendirmesi raporunu oluşturur.

        Parametreler:
            discriminator  : Eğitilmiş GANDiscriminator nesnesi
            validator      : StatisticalValidator nesnesi
            real_data      : Gerçek bankacılık verisi
            synthetic_data : Sentetik olarak üretilmiş veri

        Döner:
            Doldurulmuş DiscriminatorReport nesnesi

        Kaldırır:
            RuntimeError: Discriminator eğitilmemişse
        """
        report = cls()
        report._generated_at = datetime.now().isoformat()

        logger.info("Discriminator raporu oluşturuluyor...")

        # 1. Discriminator metrikleri
        # Gerçek + sentetik etiketlerle birleştir
        n_real = len(real_data)
        n_syn = len(synthetic_data)
        combined = pd.concat([real_data, synthetic_data], ignore_index=True)
        labels = np.hstack([np.ones(n_real), np.zeros(n_syn)])

        metrics = discriminator.evaluate(combined, labels=labels)

        # 2. İstatistiksel testler
        stat_results = validator.run_all_tests(real_data, synthetic_data)

        # 3. Özellik önemi
        feat_imp = discriminator.feature_importance(synthetic_data)

        # 4. Discriminator puanı
        disc_score = discriminator.get_discriminator_score(synthetic_data)

        # 5. Kalite değerlendirmesi
        quality_assessment = cls._assess_quality(
            disc_score=disc_score,
            metrics=metrics,
            stat_results=stat_results,
        )

        # Raporu derle
        report._report = {
            "rapor_tarihi": report._generated_at,
            "veri_ozeti": {
                "gercek_ornek_sayisi": n_real,
                "sentetik_ornek_sayisi": n_syn,
                "sutun_sayisi": len(real_data.columns),
                "sutunlar": list(real_data.columns),
            },
            "discriminator_metrikleri": metrics.to_dict(),
            "istatistiksel_testler": stat_results,
            "ozellik_onemi": feat_imp,
            "discriminator_puani": disc_score,
            "kalite_degerlendirmesi": quality_assessment,
            "egitim_gecmisi": {
                "son_kayip": metrics.loss_history[-1] if metrics.loss_history else None,
                "son_dogruluk": metrics.accuracy_history[-1] if metrics.accuracy_history else None,
                "epok_sayisi": len(metrics.loss_history),
            }
        }

        logger.info(f"Rapor oluşturuldu: discriminator_puanı={disc_score:.4f}")
        return report

    @staticmethod
    def _assess_quality(
        disc_score: float,
        metrics: DiscriminatorMetrics,
        stat_results: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Genel kalite değerlendirmesi yapar.

        Discriminator puanı, istatistiksel test geçme oranı ve
        doğruluk metriklerine göre kalite seviyesi belirlenir.

        Parametreler:
            disc_score  : GANDiscriminator kalite puanı
            metrics     : DiscriminatorMetrics nesnesi
            stat_results: İstatistiksel test sonuçları

        Döner:
            Kalite değerlendirmesi sözlüğü
        """
        # Kalite seviyesi belirleme
        if disc_score >= 0.85:
            quality_level = "Mükemmel"
            quality_emoji_text = "[MUKEMMEL]"
        elif disc_score >= 0.70:
            quality_level = "İyi"
            quality_emoji_text = "[IYI]"
        elif disc_score >= 0.50:
            quality_level = "Orta"
            quality_emoji_text = "[ORTA]"
        elif disc_score >= 0.30:
            quality_level = "Düşük"
            quality_emoji_text = "[DUSUK]"
        else:
            quality_level = "Çok Düşük"
            quality_emoji_text = "[COK DUSUK]"

        # İstatistiksel test özeti
        stat_summary = stat_results.get('summary', {})
        pass_rate = stat_summary.get('pass_rate', 0.0)
        overall_stat_score = stat_results.get('overall_score', 0.0)

        # Öneriler
        recommendations = []
        if disc_score < 0.5:
            recommendations.append(
                "Discriminator sentetik veriyi kolaylıkla ayırt edebiliyor. "
                "Üretim modelinin parametrelerini gözden geçirin."
            )
        if metrics.accuracy > 0.8:
            recommendations.append(
                "Yüksek discriminator doğruluğu, sentetik verinin gerçek veriden "
                "önemli ölçüde farklı olduğunu gösteriyor."
            )
        if pass_rate < 0.5:
            recommendations.append(
                "İstatistiksel testlerin yarısından fazlası başarısız. "
                "Veri dağılımları kontrol edilmeli."
            )
        if not recommendations:
            recommendations.append(
                "Sentez kalitesi kabul edilebilir düzeydedir. "
                "Düzenli izlemeye devam edin."
            )

        return {
            "kalite_seviyesi": quality_level,
            "kalite_etiketi": quality_emoji_text,
            "discriminator_puani": disc_score,
            "istatistiksel_gecme_orani": pass_rate,
            "genel_istatistiksel_puan": overall_stat_score,
            "oneriler": recommendations,
        }

    def to_dict(self) -> Dict[str, Any]:
        """
        Raporu JSON serileştirilebilir sözlüğe çevirir.

        Döner:
            Tüm rapor verilerini içeren sözlük

        Kaldırır:
            ValueError: Rapor henüz oluşturulmamışsa
        """
        if not self._report:
            raise ValueError("Rapor henüz oluşturulmadı. generate() metodunu çağırın.")
        return self._report.copy()

    def summary_text(self) -> str:
        """
        İnsan okunabilir özet metin oluşturur.

        Döner:
            Biçimlendirilmiş rapor metni

        Kaldırır:
            ValueError: Rapor henüz oluşturulmamışsa
        """
        if not self._report:
            raise ValueError("Rapor henüz oluşturulmadı. generate() metodunu çağırın.")

        r = self._report
        metrics = r.get("discriminator_metrikleri", {})
        quality = r.get("kalite_degerlendirmesi", {})
        stat_sum = r.get("istatistiksel_testler", {}).get("summary", {})
        feat_imp = r.get("ozellik_onemi", {})
        veri = r.get("veri_ozeti", {})

        # Rapor metnini oluştur
        lines = [
            "=" * 70,
            "  GAN DISKRİMİNATÖR KALİTE RAPORU",
            "=" * 70,
            f"  Rapor Tarihi : {r.get('rapor_tarihi', 'N/A')}",
            "-" * 70,
            "",
            "VERİ ÖZETİ:",
            f"  Gerçek Örnek Sayısı  : {veri.get('gercek_ornek_sayisi', 'N/A')}",
            f"  Sentetik Örnek Sayısı: {veri.get('sentetik_ornek_sayisi', 'N/A')}",
            f"  Sütun Sayısı         : {veri.get('sutun_sayisi', 'N/A')}",
            "",
            "KALİTE DEĞERLENDİRMESİ:",
            f"  Kalite Seviyesi      : {quality.get('kalite_seviyesi', 'N/A')}",
            f"  Discriminator Puanı  : {quality.get('discriminator_puani', 0.0):.4f}",
            f"  (0.5 = Mükemmel Sentez, 1.0 = Tamamen Gerçek, 0.0 = Tamamen Sentetik)",
            "",
            "DİSKRİMİNATÖR METRİKLERİ:",
            f"  Doğruluk (Accuracy)  : {metrics.get('accuracy', 0.0):.4f}",
            f"  Kesinlik (Precision) : {metrics.get('precision', 0.0):.4f}",
            f"  Duyarlılık (Recall)  : {metrics.get('recall', 0.0):.4f}",
            f"  F1 Skoru             : {metrics.get('f1_score', 0.0):.4f}",
            f"  AUC-ROC              : {metrics.get('auc_roc', 0.0):.4f}",
            "",
            "İSTATİSTİKSEL TESTLER:",
            f"  Toplam Test          : {stat_sum.get('total_tests', 0)}",
            f"  Geçen Test           : {stat_sum.get('passed_tests', 0)}",
            f"  Başarısız Test       : {stat_sum.get('failed_tests', 0)}",
            f"  Geçme Oranı          : {stat_sum.get('pass_rate', 0.0):.2%}",
            "",
            "EN ÖNEMLİ ÖZELLİKLER (İlk 5):",
        ]

        # İlk 5 özellik
        for i, (feat, imp) in enumerate(list(feat_imp.items())[:5], 1):
            lines.append(f"  {i}. {feat:<30} : {imp:.4f}")

        lines += [
            "",
            "ÖNERİLER:",
        ]
        for rec in quality.get("oneriler", []):
            lines.append(f"  * {rec}")

        lines += [
            "",
            "EĞİTİM GEÇMİŞİ:",
            f"  Epok Sayısı          : {r.get('egitim_gecmisi', {}).get('epok_sayisi', 0)}",
            f"  Son Kayıp            : {r.get('egitim_gecmisi', {}).get('son_kayip', 'N/A')}",
            f"  Son Doğruluk         : {r.get('egitim_gecmisi', {}).get('son_dogruluk', 'N/A')}",
            "",
            "=" * 70,
        ]

        return "\n".join(lines)

    def to_json(self, indent: int = 2) -> str:
        """
        Raporu JSON dizgisine dönüştürür.

        Parametreler:
            indent: JSON girintisi (varsayılan 2)

        Döner:
            JSON biçimli rapor dizgisi
        """
        def _make_serializable(obj: Any) -> Any:
            """NumPy/pandas nesnelerini JSON serileştirilebilir yapar."""
            if isinstance(obj, np.ndarray):
                return obj.tolist()
            elif isinstance(obj, (np.integer, np.int64, np.int32)):
                return int(obj)
            elif isinstance(obj, (np.floating, np.float64, np.float32)):
                return float(obj)
            elif isinstance(obj, dict):
                return {k: _make_serializable(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [_make_serializable(v) for v in obj]
            return obj

        return json.dumps(_make_serializable(self.to_dict()), indent=indent, ensure_ascii=False)

    def __repr__(self) -> str:
        if self._generated_at:
            return f"DiscriminatorReport(generated_at={self._generated_at})"
        return "DiscriminatorReport(henüz oluşturulmadı)"


# ===========================================================================
# Modül Düzeyinde Yardımcı Fonksiyonlar
# ===========================================================================

def quick_evaluate(
    real_data: pd.DataFrame,
    synthetic_data: pd.DataFrame,
    hidden_layers: Optional[List[int]] = None,
    epochs: int = 50,
) -> Dict[str, Any]:
    """
    Hızlı discriminator değerlendirmesi için kolaylık fonksiyonu.

    Tek fonksiyon çağrısıyla discriminator eğitir ve tam rapor döner.

    Parametreler:
        real_data    : Gerçek bankacılık verisi
        synthetic_data: Sentetik veri
        hidden_layers: Gizli katman boyutları (varsayılan [64, 32])
        epochs       : Eğitim epok sayısı (varsayılan 50)

    Döner:
        Rapor sözlüğü (to_dict() çıktısıyla aynı format)
    """
    if hidden_layers is None:
        hidden_layers = [64, 32]

    disc = GANDiscriminator(
        hidden_layers=hidden_layers,
        epochs=epochs,
        learning_rate=0.001,
        batch_size=32,
    )

    disc.train(real_data, synthetic_data)
    validator = StatisticalValidator()
    report = DiscriminatorReport.generate(disc, validator, real_data, synthetic_data)
    return report.to_dict()


def compute_privacy_score(
    real_data: pd.DataFrame,
    synthetic_data: pd.DataFrame,
    n_neighbors: int = 5,
) -> Dict[str, float]:
    """
    Sentetik verinin gizlilik riskini mesafe tabanlı olarak değerlendirir.

    Her sentetik örnek için en yakın gerçek örneğin mesafesi hesaplanır.
    Düşük ortalama mesafe yüksek gizlilik riski anlamına gelir.

    Parametreler:
        real_data    : Gerçek veri
        synthetic_data: Sentetik veri
        n_neighbors  : En yakın komşu sayısı

    Döner:
        Şu anahtarları içeren gizlilik metrikleri sözlüğü:
            'min_distance'    : Minimum komşu mesafesi
            'mean_distance'   : Ortalama komşu mesafesi
            'privacy_score'   : [0,1] gizlilik puanı (1 = yüksek gizlilik)
    """
    # Yalnızca sayısal sütunlar
    num_cols = [c for c in real_data.columns
                if pd.api.types.is_numeric_dtype(real_data[c]) and c in synthetic_data.columns]

    if not num_cols:
        return {
            "min_distance": float('inf'),
            "mean_distance": float('inf'),
            "privacy_score": 1.0,
            "uyari": "Sayısal sütun bulunamadı"
        }

    r = real_data[num_cols].fillna(0).values.astype(float)
    s = synthetic_data[num_cols].fillna(0).values.astype(float)

    # Normalize et
    std = np.std(r, axis=0)
    std[std < _EPS] = 1.0
    r_norm = r / std
    s_norm = s / std

    # Her sentetik örnek için en yakın n_neighbors gerçek örneği bul
    n_syn = min(len(s_norm), 500)  # Hız için örnekle
    s_sample = s_norm[:n_syn]

    min_dists = []
    for syn_row in s_sample:
        dists = np.linalg.norm(r_norm - syn_row, axis=1)
        top_k = np.sort(dists)[:n_neighbors]
        min_dists.append(float(np.mean(top_k)))

    mean_dist = float(np.mean(min_dists))
    min_dist = float(np.min(min_dists))

    # Gizlilik puanı: mesafe ne kadar büyükse o kadar güvenli
    # Referans: n_features boyutunda beklenen mesafe ~ sqrt(n_features)
    n_features = len(num_cols)
    expected_dist = np.sqrt(n_features)
    privacy_score = float(np.clip(mean_dist / (expected_dist + _EPS), 0.0, 1.0))

    return {
        "min_distance": min_dist,
        "mean_distance": mean_dist,
        "privacy_score": privacy_score,
        "n_real_samples": len(r),
        "n_synthetic_samples_evaluated": n_syn,
        "n_neighbors": n_neighbors,
    }
