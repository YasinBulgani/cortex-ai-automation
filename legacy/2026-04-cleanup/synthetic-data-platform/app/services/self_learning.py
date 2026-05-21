"""
Kendi Kendini Öğrenen Veri Analiz ve Optimizasyon Motoru.

Bu modül, sentetik veri üretim sürecini izlemek, geri bildirim toplamak,
kalite metriklerini analiz etmek ve sistem parametrelerini otomatik olarak
optimize etmek için bir kendi kendini öğrenen mekanizması sağlar.
"""

import json
import logging
import random
import statistics
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.config import settings
from app.models.database import SessionLocal, get_db
from app.models.learning_models import (
    FeedbackType,
    GenerationMetrics,
    LearnedPattern,
    LearningFeedback,
    OptimizationHistory,
    OptimizationType,
    PatternType,
)


logger = logging.getLogger(__name__)


class SelfLearningEngine:
    """
    Kendi kendini öğrenen motor ana sınıfı.

    Sentetik veri üretiminden geri bildirim toplar, kalite metriklerini izler,
    örüntüleri öğrenir ve sistem parametrelerini otomatik olarak optimize eder.
    """

    def __init__(self):
        """Öğrenme motorunu başlatır."""
        self.feedback_collector = FeedbackCollector()
        self.pattern_learner = PatternLearner()
        self.quality_optimizer = QualityOptimizer()
        self.rule_recommender = RuleRecommender()
        self.model_weight_adjuster = ModelWeightAdjuster()
        self.epsilon = 0.2  # 20% keşfet, 80% istismarla

        logger.info(
            "Kendi kendini öğrenen motor başlatıldı. Epsilon değeri: %.2f",
            self.epsilon
        )

    @property
    def _knowledge_base_dir(self) -> Path:
        """
        Bilgi tabanı dizinine giden yolu döndürür.

        Dönüş:
            Path: Bilgi tabanı dosyalarının depolandığı dizin.
        """
        kb_dir = Path(settings.BASE_DIR) / "data" / "knowledge_base"
        kb_dir.mkdir(parents=True, exist_ok=True)
        return kb_dir

    def _load_knowledge(self, filename: str) -> Dict[str, Any]:
        """
        JSON dosyasından bilgi yükler.

        Argümanlar:
            filename: Yüklenecek dosya adı.

        Dönüş:
            Dict[str, Any]: Dosyadan okunan veriler veya boş sözlük.
        """
        filepath = self._knowledge_base_dir / filename
        if not filepath.exists():
            logger.debug("Bilgi tabanı dosyası bulunamadı: %s", filepath)
            return {}

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                logger.debug("Bilgi yüklendi: %s (%d kayıt)", filename, len(data))
                return data
        except Exception as e:
            logger.error("Bilgi yüklenirken hata: %s - %s", filename, e)
            return {}

    def _save_knowledge(self, filename: str, data: Dict[str, Any]) -> bool:
        """
        Bilgiyi JSON dosyasına kaydeder.

        Argümanlar:
            filename: Kaydedilecek dosya adı.
            data: Kaydedilecek veriler.

        Dönüş:
            bool: İşlem başarılı olsa True, aksi halde False.
        """
        filepath = self._knowledge_base_dir / filename

        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                logger.debug("Bilgi kaydedildi: %s (%d kayıt)", filename, len(data))
                return True
        except Exception as e:
            logger.error("Bilgi kaydedilirken hata: %s - %s", filename, e)
            return False

    def sync_to_knowledge_base(self, session: Session) -> Dict[str, int]:
        """
        Veritabanındaki öğrenilmiş örüntüleri bilgi tabanına dışa aktarır.

        Argümanlar:
            session: Veritabanı oturumu.

        Dönüş:
            Dict[str, int]: Dışa aktarılan kayıt sayıları.
        """
        logger.info("Bilgi tabanına senkronizasyon başlatıldı")

        patterns = session.query(LearnedPattern).all()
        pattern_dict = {
            p.id: {
                'pattern_type': p.pattern_type.value,
                'pattern_data': p.pattern_data,
                'confidence': p.confidence,
                'created_at': p.created_at.isoformat() if p.created_at else None,
            }
            for p in patterns
        }

        metrics = session.query(GenerationMetrics).all()
        metrics_dict = {
            m.id: {
                'job_id': m.job_id,
                'dataset_id': m.dataset_id,
                'quality_score': m.quality_score,
                'execution_time_ms': m.execution_time_ms,
                'memory_usage_mb': m.memory_usage_mb,
                'created_at': m.created_at.isoformat() if m.created_at else None,
            }
            for m in metrics
        }

        feedbacks = session.query(LearningFeedback).all()
        feedback_dict = {
            f.id: {
                'feedback_type': f.feedback_type.value,
                'rating': f.rating,
                'aspects': f.aspects,
                'created_at': f.created_at.isoformat() if f.created_at else None,
            }
            for f in feedbacks
        }

        success_count = 0
        success_count += self._save_knowledge("patterns.json", pattern_dict)
        success_count += self._save_knowledge("metrics.json", metrics_dict)
        success_count += self._save_knowledge("feedbacks.json", feedback_dict)

        result = {
            'patterns': len(pattern_dict),
            'metrics': len(metrics_dict),
            'feedbacks': len(feedback_dict),
            'files_saved': success_count,
        }

        logger.info("Bilgi tabanı senkronizasyonu tamamlandı: %s", result)
        return result

    def load_from_knowledge_base(self, session: Session) -> Dict[str, int]:
        """
        Bilgi tabanından öğrenilmiş örüntüleri veritabanına aktarır.

        Argümanlar:
            session: Veritabanı oturumu.

        Dönüş:
            Dict[str, int]: İthal edilen kayıt sayıları.
        """
        logger.info("Bilgi tabanından ithalatçı başlatıldı")

        imported_count = {'patterns': 0, 'metrics': 0}

        pattern_dict = self._load_knowledge("patterns.json")
        for pattern_id, pattern_data in pattern_dict.items():
            try:
                pattern = LearnedPattern(
                    pattern_type=PatternType(pattern_data['pattern_type']),
                    pattern_data=pattern_data['pattern_data'],
                    confidence=pattern_data['confidence'],
                )
                session.add(pattern)
                imported_count['patterns'] += 1
            except Exception as e:
                logger.warning("Örüntü ithal edilirken hata: %s", e)

        metrics_dict = self._load_knowledge("metrics.json")
        for metrics_id, metrics_data in metrics_dict.items():
            try:
                metrics = GenerationMetrics(
                    job_id=metrics_data.get('job_id'),
                    dataset_id=metrics_data.get('dataset_id'),
                    quality_score=metrics_data.get('quality_score'),
                    execution_time_ms=metrics_data.get('execution_time_ms'),
                    memory_usage_mb=metrics_data.get('memory_usage_mb'),
                )
                session.add(metrics)
                imported_count['metrics'] += 1
            except Exception as e:
                logger.warning("Metrik ithal edilirken hata: %s", e)

        try:
            session.commit()
            logger.info("Bilgi tabanı ithalatı tamamlandı: %s", imported_count)
        except Exception as e:
            logger.error("Bilgi tabanı ithalatı kaydedilirken hata: %s", e)
            session.rollback()

        return imported_count

    def select_parameters(
        self, session: Session, scenario_type: str
    ) -> Dict[str, Any]:
        """
        Epsilon-açgözlü strateji kullanarak parametreleri seçer.

        %80 olasılıkla bilinen en iyi parametreleri kullanır,
        %20 olasılıkla yeni parametreleri keşfeder.

        Argümanlar:
            session: Veritabanı oturumu.
            scenario_type: Senaryo türü.

        Dönüş:
            Dict[str, Any]: Seçilen parametreler.
        """
        if random.random() < (1 - self.epsilon):
            logger.debug(
                "İstismarı seçildi (%.1f%%) - en iyi parametreler",
                (1 - self.epsilon) * 100
            )
            return self._exploit_best_params(session, scenario_type)
        else:
            logger.debug(
                "Keşfi seçildi (%.1f%%) - yeni parametreler",
                self.epsilon * 100
            )
            return self._explore_new_params(scenario_type)

    def _exploit_best_params(
        self, session: Session, scenario_type: str
    ) -> Dict[str, Any]:
        """
        Bilinen en iyi parametreleri döndürür.

        Argümanlar:
            session: Veritabanı oturumu.
            scenario_type: Senaryo türü.

        Dönüş:
            Dict[str, Any]: En iyi parametreler.
        """
        patterns = session.query(LearnedPattern).filter(
            LearnedPattern.pattern_type == PatternType.SCENARIO_CONFIG
        ).order_by(LearnedPattern.confidence.desc()).first()

        if patterns and patterns.pattern_data:
            logger.debug("En iyi parametreler bulunamadı, varsayılanlar döndürülüyor")
            return patterns.pattern_data.get('params', self._get_default_params())

        return self._get_default_params()

    def _explore_new_params(self, scenario_type: str) -> Dict[str, Any]:
        """
        Mevcut parametrelere rastgele varyasyonlar uygular.

        Argümanlar:
            scenario_type: Senaryo türü.

        Dönüş:
            Dict[str, Any]: Yeni parametreler.
        """
        base_params = self._get_default_params()

        explored_params = base_params.copy()
        explored_params['batch_size'] = random.randint(
            settings.DEFAULT_BATCH_SIZE,
            settings.MAX_BATCH_SIZE
        )
        explored_params['parallelism'] = random.randint(1, 8)
        explored_params['cache_enabled'] = random.choice([True, False])
        explored_params['exploration_iteration'] = True

        logger.debug("Keşfedilen parametreler: %s", explored_params)
        return explored_params

    def _get_default_params(self) -> Dict[str, Any]:
        """
        Varsayılan parametreleri döndürür.

        Dönüş:
            Dict[str, Any]: Varsayılan parametreler.
        """
        return {
            'batch_size': settings.DEFAULT_BATCH_SIZE,
            'parallelism': 4,
            'cache_enabled': True,
            'rule_weight_threshold': 0.5,
            'quality_target': 0.85,
        }

    def get_insights(self, session: Session) -> Dict[str, Any]:
        """
        Kapsamlı öğrenme içgörüleri sağlar.

        Argümanlar:
            session: Veritabanı oturumu.

        Dönüş:
            Dict[str, Any]: İçgörüler ve analiz sonuçları.
        """
        logger.info("İçgörüler toplanıyor")

        feedback_summary = self.feedback_collector.get_feedback_summary(session)
        quality_trend = self.feedback_collector.get_quality_trend(session)
        best_patterns = self.pattern_learner.get_best_patterns(session)
        performance_summary = self.get_performance_summary(session)

        insights = {
            'timestamp': datetime.utcnow().isoformat(),
            'feedback_summary': feedback_summary,
            'quality_trend': quality_trend,
            'best_patterns_count': len(best_patterns),
            'performance_summary': performance_summary,
            'total_feedback_records': session.query(LearningFeedback).count(),
            'total_metrics_records': session.query(GenerationMetrics).count(),
            'total_patterns': session.query(LearnedPattern).count(),
        }

        logger.debug("İçgörüler: %s", insights)
        return insights

    def get_recommendations(
        self, session: Session, column_profiles: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """
        Sistemi geliştirmek için öneriler sağlar.

        Argümanlar:
            session: Veritabanı oturumu.
            column_profiles: Sütun profillerinin listesi (opsiyonel).

        Dönüş:
            Dict[str, Any]: Öneriler ve tavsiyeler.
        """
        logger.info("Öneriler oluşturuluyor")

        recommendations = {
            'timestamp': datetime.utcnow().isoformat(),
            'rule_recommendations': [],
            'optimization_suggestions': [],
            'pattern_insights': [],
        }

        if column_profiles:
            rule_recs = self.rule_recommender.recommend_rules(session, column_profiles)
            recommendations['rule_recommendations'] = rule_recs

        optimization_opts = self.quality_optimizer.optimize_parameters(session)
        recommendations['optimization_suggestions'] = optimization_opts

        best_patterns = self.pattern_learner.get_best_patterns(session, min_confidence=0.7)
        recommendations['pattern_insights'] = [
            {
                'pattern_type': p.pattern_type.value,
                'confidence': p.confidence,
                'summary': str(p.pattern_data)[:200],
            }
            for p in best_patterns[:5]
        ]

        logger.debug("Öneriler hazırlandı: %d kural, %d optimizasyon",
                     len(recommendations['rule_recommendations']),
                     len(recommendations['optimization_suggestions']))

        return recommendations

    def record_generation_metrics(
        self,
        session: Session,
        job_id: str,
        dataset_id: str,
        scenario: str,
        row_count: int,
        col_count: int,
        time_ms: float,
        memory_mb: float,
        quality_score: float,
        scores_dict: Dict[str, float],
        params: Dict[str, Any],
        rule_scores: Dict[str, float],
    ) -> GenerationMetrics:
        """
        Veri üretim metriklerini kaydeder.

        Argümanlar:
            session: Veritabanı oturumu.
            job_id: İş kimliği.
            dataset_id: Veri seti kimliği.
            scenario: Senaryo adı.
            row_count: Üretilen satır sayısı.
            col_count: Sütun sayısı.
            time_ms: İşlem süresi (milisaniye).
            memory_mb: Bellek kullanımı (MB).
            quality_score: Genel kalite puanı (0-1).
            scores_dict: Kalite boyutlarının puanları.
            params: Kullanılan parametreler.
            rule_scores: Kural puanları.

        Dönüş:
            GenerationMetrics: Kaydedilen metrik.
        """
        logger.info(
            "Metrikler kaydediliyor: job=%s, kalite=%.2f, süre=%.0fms",
            job_id, quality_score, time_ms
        )

        metrics = GenerationMetrics(
            job_id=job_id,
            dataset_id=dataset_id,
            scenario=scenario,
            row_count=row_count,
            column_count=col_count,
            execution_time_ms=time_ms,
            memory_usage_mb=memory_mb,
            quality_score=quality_score,
            quality_scores=scores_dict,
            generation_params=params,
            rule_scores=rule_scores,
        )

        session.add(metrics)
        session.commit()

        logger.debug("Metrikler kaydedildi, ID: %s", metrics.id)
        return metrics

    def get_performance_summary(self, session: Session) -> Dict[str, Any]:
        """
        Performans metriklerinin özet istatistiklerini döndürür.

        Argümanlar:
            session: Veritabanı oturumu.

        Dönüş:
            Dict[str, Any]: Özet istatistikler.
        """
        metrics_records = session.query(GenerationMetrics).all()

        if not metrics_records:
            logger.warning("Performans metriği kaydı bulunamadı")
            return {
                'total_jobs': 0,
                'avg_quality_score': 0.0,
                'avg_execution_time_ms': 0.0,
                'avg_memory_mb': 0.0,
            }

        quality_scores = [m.quality_score for m in metrics_records if m.quality_score]
        times = [m.execution_time_ms for m in metrics_records if m.execution_time_ms]
        memory = [m.memory_usage_mb for m in metrics_records if m.memory_usage_mb]

        summary = {
            'total_jobs': len(metrics_records),
            'avg_quality_score': statistics.mean(quality_scores) if quality_scores else 0.0,
            'min_quality_score': min(quality_scores) if quality_scores else 0.0,
            'max_quality_score': max(quality_scores) if quality_scores else 0.0,
            'avg_execution_time_ms': statistics.mean(times) if times else 0.0,
            'avg_memory_mb': statistics.mean(memory) if memory else 0.0,
        }

        logger.debug("Performans özeti: %s", summary)
        return summary

    def get_quality_dimensions_summary(self, session: Session) -> Dict[str, float]:
        """
        Kalite boyutlarının ortalama puanlarını döndürür.

        Argümanlar:
            session: Veritabanı oturumu.

        Dönüş:
            Dict[str, float]: Boyut başına ortalama puanlar.
        """
        metrics_records = session.query(GenerationMetrics).all()

        dimension_scores = {}

        for metrics in metrics_records:
            if metrics.quality_scores:
                for dimension, score in metrics.quality_scores.items():
                    if dimension not in dimension_scores:
                        dimension_scores[dimension] = []
                    dimension_scores[dimension].append(score)

        summary = {
            dimension: statistics.mean(scores)
            for dimension, scores in dimension_scores.items()
            if scores
        }

        logger.debug("Kalite boyutları özeti: %d boyut", len(summary))
        return summary

    def reset_learning_data(
        self,
        session: Session,
        reset_feedbacks: bool = True,
        reset_patterns: bool = True,
        reset_metrics: bool = False,
    ) -> Dict[str, int]:
        """
        Öğrenilmiş verileri sıfırlar.

        Argümanlar:
            session: Veritabanı oturumu.
            reset_feedbacks: Geri bildirimleri sıfırla.
            reset_patterns: Örüntüleri sıfırla.
            reset_metrics: Metrikleri sıfırla.

        Dönüş:
            Dict[str, int]: Silinen kayıt sayıları.
        """
        logger.warning(
            "Öğrenilmiş veriler sıfırlanıyor (geri bildirimler: %s, "
            "örüntüler: %s, metrikler: %s)",
            reset_feedbacks, reset_patterns, reset_metrics
        )

        deleted_count = {'feedbacks': 0, 'patterns': 0, 'metrics': 0}

        if reset_feedbacks:
            deleted_count['feedbacks'] = (
                session.query(LearningFeedback).delete()
            )

        if reset_patterns:
            deleted_count['patterns'] = (
                session.query(LearnedPattern).delete()
            )

        if reset_metrics:
            deleted_count['metrics'] = (
                session.query(GenerationMetrics).delete()
            )

        session.commit()
        logger.info("Veriler sıfırlandı: %s", deleted_count)
        return deleted_count


class FeedbackCollector:
    """
    Veri üretim sürecinden geri bildirim toplar ve analiz eder.
    """

    def collect_feedback(
        self,
        session: Session,
        feedback_data: Dict[str, Any],
    ) -> LearningFeedback:
        """
        Yeni geri bildirim kaydeder.

        Argümanlar:
            session: Veritabanı oturumu.
            feedback_data: Geri bildirim verileri.
                - feedback_type: str (FeedbackType değeri)
                - rating: int (1-5 arası)
                - dataset_id: str (opsiyonel)
                - aspects: dict (opsiyonel, detaylı geri bildirim)

        Dönüş:
            LearningFeedback: Kaydedilen geri bildirim.
        """
        logger.info("Geri bildirim kaydediliyor: %s", feedback_data)

        feedback = LearningFeedback(
            feedback_type=FeedbackType(feedback_data.get('feedback_type')),
            rating=feedback_data.get('rating', 3),
            dataset_id=feedback_data.get('dataset_id'),
            aspects=feedback_data.get('aspects', {}),
        )

        session.add(feedback)
        session.commit()

        logger.debug("Geri bildirim kaydedildi, ID: %s", feedback.id)
        return feedback

    def get_feedback_summary(
        self, session: Session, dataset_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Geri bildirimlerin özet istatistiklerini döndürür.

        Argümanlar:
            session: Veritabanı oturumu.
            dataset_id: Belirli veri setine ait geri bildirimleri filtrele.

        Dönüş:
            Dict[str, Any]: Özet istatistikler.
        """
        query = session.query(LearningFeedback)

        if dataset_id:
            query = query.filter(LearningFeedback.dataset_id == dataset_id)

        feedbacks = query.all()

        if not feedbacks:
            logger.debug("Geri bildirim kaydı bulunamadı")
            return {
                'total_feedback': 0,
                'average_rating': 0.0,
                'rating_distribution': {},
                'top_positive_aspects': [],
                'top_negative_aspects': [],
            }

        ratings = [f.rating for f in feedbacks if f.rating]
        rating_distribution = {}
        for rating in ratings:
            rating_distribution[rating] = rating_distribution.get(rating, 0) + 1

        positive_aspects = {}
        negative_aspects = {}

        for feedback in feedbacks:
            if feedback.aspects:
                for aspect, value in feedback.aspects.items():
                    if isinstance(value, bool) or isinstance(value, (int, float)):
                        if value:
                            positive_aspects[aspect] = (
                                positive_aspects.get(aspect, 0) + 1
                            )
                        else:
                            negative_aspects[aspect] = (
                                negative_aspects.get(aspect, 0) + 1
                            )

        top_positive = sorted(
            positive_aspects.items(), key=lambda x: x[1], reverse=True
        )[:3]
        top_negative = sorted(
            negative_aspects.items(), key=lambda x: x[1], reverse=True
        )[:3]

        summary = {
            'total_feedback': len(feedbacks),
            'average_rating': (
                statistics.mean(ratings) if ratings else 0.0
            ),
            'rating_distribution': rating_distribution,
            'top_positive_aspects': [a[0] for a in top_positive],
            'top_negative_aspects': [a[0] for a in top_negative],
        }

        logger.debug("Geri bildirim özeti: %s", summary)
        return summary

    def get_quality_trend(
        self, session: Session, days: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Son n günün günlük kalite eğilimini döndürür.

        Argümanlar:
            session: Veritabanı oturumu.
            days: Kaç gün geriye bakılacak.

        Dönüş:
            List[Dict[str, Any]]: Günlük ortalama puanlar.
        """
        start_date = datetime.utcnow() - timedelta(days=days)

        feedbacks = session.query(LearningFeedback).filter(
            LearningFeedback.created_at >= start_date
        ).all()

        daily_ratings = {}
        for feedback in feedbacks:
            if feedback.created_at and feedback.rating:
                day = feedback.created_at.date()
                if day not in daily_ratings:
                    daily_ratings[day] = []
                daily_ratings[day].append(feedback.rating)

        trend = [
            {
                'date': day.isoformat(),
                'average_rating': statistics.mean(ratings),
                'feedback_count': len(ratings),
            }
            for day, ratings in sorted(daily_ratings.items())
        ]

        logger.debug("Kalite eğilimi: %d gün", len(trend))
        return trend


class PatternLearner:
    """
    Veri üretim sonuçlarından örüntüleri öğrenir.
    """

    def learn_from_generation(
        self,
        session: Session,
        generation_job_id: str,
        quality_score: float,
        params: Dict[str, Any],
    ) -> List[LearnedPattern]:
        """
        Bir veri üretim işinden öğrenir ve örüntüler kaydeder.

        Argümanlar:
            session: Veritabanı oturumu.
            generation_job_id: İş kimliği.
            quality_score: Kalite puanı (0-1).
            params: Üretimde kullanılan parametreler.

        Dönüş:
            List[LearnedPattern]: Öğrenilmiş örüntüleri.
        """
        logger.info(
            "Üretimden öğreniliyor: job=%s, kalite=%.2f",
            generation_job_id, quality_score
        )

        patterns = []

        column_pattern = self._learn_column_mapping(params, quality_score)
        if column_pattern:
            pattern = LearnedPattern(
                pattern_type=PatternType.COLUMN_MAPPING,
                pattern_data=column_pattern,
                confidence=min(quality_score, 0.95),
            )
            session.add(pattern)
            patterns.append(pattern)

        dist_pattern = self._learn_distribution_fit(params, quality_score)
        if dist_pattern:
            pattern = LearnedPattern(
                pattern_type=PatternType.DISTRIBUTION_FIT,
                pattern_data=dist_pattern,
                confidence=min(quality_score, 0.95),
            )
            session.add(pattern)
            patterns.append(pattern)

        rule_pattern = self._learn_rule_combination(params, quality_score)
        if rule_pattern:
            pattern = LearnedPattern(
                pattern_type=PatternType.RULE_COMBINATION,
                pattern_data=rule_pattern,
                confidence=min(quality_score, 0.95),
            )
            session.add(pattern)
            patterns.append(pattern)

        scenario_pattern = self._learn_scenario_config(params, quality_score)
        if scenario_pattern:
            pattern = LearnedPattern(
                pattern_type=PatternType.SCENARIO_CONFIG,
                pattern_data=scenario_pattern,
                confidence=min(quality_score, 0.95),
            )
            session.add(pattern)
            patterns.append(pattern)

        session.commit()

        logger.info("Öğrenilmiş örüntüler kaydedildi: %d adet", len(patterns))
        return patterns

    def _learn_column_mapping(
        self, params: Dict[str, Any], quality_score: float
    ) -> Optional[Dict[str, Any]]:
        """
        Sütun eşlemesi örüntülerini öğrenir.

        Hangi üretici işlevi hangi sütun türü için en iyi sonuç verdiğini
        belirlemek amacıyla kullanılır.

        Argümanlar:
            params: Parametreler sözlüğü.
            quality_score: Kalite puanı.

        Dönüş:
            Optional[Dict[str, Any]]: Öğrenilmiş örüntü.
        """
        if 'column_type_strategy' not in params:
            return None

        pattern = {
            'strategy': params.get('column_type_strategy'),
            'quality_score': quality_score,
            'timestamp': datetime.utcnow().isoformat(),
        }

        logger.debug("Sütun eşlemesi örüntüsü öğrenildi: %s", pattern)
        return pattern

    def _learn_distribution_fit(
        self, params: Dict[str, Any], quality_score: float
    ) -> Optional[Dict[str, Any]]:
        """
        Dağılım uydurma örüntülerini öğrenir.

        Hangi dağılımın hangi sütun türü için en uygun olduğunu belirler.

        Argümanlar:
            params: Parametreler sözlüğü.
            quality_score: Kalite puanı.

        Dönüş:
            Optional[Dict[str, Any]]: Öğrenilmiş örüntü.
        """
        if 'distribution_fit' not in params:
            return None

        pattern = {
            'distribution_type': params.get('distribution_fit'),
            'quality_score': quality_score,
            'timestamp': datetime.utcnow().isoformat(),
        }

        logger.debug("Dağılım örüntüsü öğrenildi: %s", pattern)
        return pattern

    def _learn_rule_combination(
        self, params: Dict[str, Any], quality_score: float
    ) -> Optional[Dict[str, Any]]:
        """
        Kural kombinasyonu örüntülerini öğrenir.

        Hangi kural kombinasyonlarının iyi sonuçlar verdiğini belirler.

        Argümanlar:
            params: Parametreler sözlüğü.
            quality_score: Kalite puanı.

        Dönüş:
            Optional[Dict[str, Any]]: Öğrenilmiş örüntü.
        """
        if 'rules' not in params:
            return None

        pattern = {
            'rules': params.get('rules'),
            'quality_score': quality_score,
            'timestamp': datetime.utcnow().isoformat(),
        }

        logger.debug("Kural kombinasyonu örüntüsü öğrenildi: %s", pattern)
        return pattern

    def _learn_scenario_config(
        self, params: Dict[str, Any], quality_score: float
    ) -> Optional[Dict[str, Any]]:
        """
        Senaryo yapılandırması örüntülerini öğrenir.

        Hangi senaryo parametrelerinin en iyi sonuç verdiğini belirler.

        Argümanlar:
            params: Parametreler sözlüğü.
            quality_score: Kalite puanı.

        Dönüş:
            Optional[Dict[str, Any]]: Öğrenilmiş örüntü.
        """
        pattern = {
            'params': params,
            'quality_score': quality_score,
            'timestamp': datetime.utcnow().isoformat(),
        }

        logger.debug("Senaryo örüntüsü öğrenildi")
        return pattern

    def get_best_patterns(
        self,
        session: Session,
        pattern_type: Optional[PatternType] = None,
        min_confidence: float = 0.5,
    ) -> List[LearnedPattern]:
        """
        En güvenilir örüntüleri döndürür.

        Argümanlar:
            session: Veritabanı oturumu.
            pattern_type: Belirli bir türe filtrele (opsiyonel).
            min_confidence: Minimum güven düzeyi.

        Dönüş:
            List[LearnedPattern]: En iyi örüntüler.
        """
        query = session.query(LearnedPattern).filter(
            LearnedPattern.confidence >= min_confidence
        ).order_by(LearnedPattern.confidence.desc())

        if pattern_type:
            query = query.filter(LearnedPattern.pattern_type == pattern_type)

        patterns = query.all()

        logger.debug(
            "En iyi örüntüler bulundu: %d adet, min_confidence=%.2f",
            len(patterns), min_confidence
        )
        return patterns


class QualityOptimizer:
    """
    Sistem parametrelerini kalite metriklerine göre optimize eder.
    """

    def optimize_parameters(
        self, session: Session, target: str = "all"
    ) -> List[Dict[str, Any]]:
        """
        Sistem parametrelerini optimize eder.

        Argümanlar:
            session: Veritabanı oturumu.
            target: Hedef ("all", "batch_size", "parallelism", vb.).

        Dönüş:
            List[Dict[str, Any]]: Optimizasyon önerileri.
        """
        logger.info("Parametreler optimize ediliyor, hedef: %s", target)

        optimizations = []

        if target in ("all", "batch_size"):
            opt = self._optimize_batch_size(session)
            if opt:
                optimizations.append(opt)

        if target in ("all", "parallelism"):
            opt = self._optimize_parallelism(session)
            if opt:
                optimizations.append(opt)

        if target in ("all", "cache_strategy"):
            opt = self._optimize_cache_strategy(session)
            if opt:
                optimizations.append(opt)

        if target in ("all", "rule_weights"):
            opt = self._optimize_rule_weights(session)
            if opt:
                optimizations.append(opt)

        if target in ("all", "generation_params"):
            opt = self._optimize_generation_params(session)
            if opt:
                optimizations.append(opt)

        logger.info("Optimizasyon tamalandı: %d öneri", len(optimizations))
        return optimizations

    def _optimize_batch_size(self, session: Session) -> Optional[Dict[str, Any]]:
        """
        Toplu iş boyutunu optimize eder.

        Argümanlar:
            session: Veritabanı oturumu.

        Dönüş:
            Optional[Dict[str, Any]]: Optimizasyon önerisi.
        """
        metrics = session.query(GenerationMetrics).all()

        if not metrics:
            return None

        batch_sizes = {}
        for m in metrics:
            if m.generation_params and 'batch_size' in m.generation_params:
                bs = m.generation_params['batch_size']
                if bs not in batch_sizes:
                    batch_sizes[bs] = []
                batch_sizes[bs].append(m.quality_score or 0)

        if not batch_sizes:
            return None

        best_batch_size = max(
            batch_sizes.items(),
            key=lambda x: statistics.mean(x[1]) if x[1] else 0
        )[0]

        optimization = {
            'parameter': 'batch_size',
            'recommended_value': best_batch_size,
            'optimization_type': OptimizationType.PERFORMANCE,
            'rationale': 'En yüksek kalite puanına göre seçildi',
        }

        logger.debug("Toplu iş boyutu optimize edildi: %d", best_batch_size)
        return optimization

    def _optimize_parallelism(self, session: Session) -> Optional[Dict[str, Any]]:
        """
        Paralelizm seviyesini optimize eder.

        Argümanlar:
            session: Veritabanı oturumu.

        Dönüş:
            Optional[Dict[str, Any]]: Optimizasyon önerisi.
        """
        metrics = session.query(GenerationMetrics).all()

        if not metrics:
            return None

        parallelism_times = {}
        for m in metrics:
            if m.generation_params and 'parallelism' in m.generation_params:
                par = m.generation_params['parallelism']
                if par not in parallelism_times:
                    parallelism_times[par] = []
                parallelism_times[par].append(m.execution_time_ms or 0)

        if not parallelism_times:
            return None

        best_parallelism = min(
            parallelism_times.items(),
            key=lambda x: statistics.mean(x[1]) if x[1] else float('inf')
        )[0]

        optimization = {
            'parameter': 'parallelism',
            'recommended_value': best_parallelism,
            'optimization_type': OptimizationType.PERFORMANCE,
            'rationale': 'En düşük işlem süresine göre seçildi',
        }

        logger.debug("Paralelizm optimize edildi: %d", best_parallelism)
        return optimization

    def _optimize_cache_strategy(self, session: Session) -> Optional[Dict[str, Any]]:
        """
        Önbellek stratejisini optimize eder.

        Argümanlar:
            session: Veritabanı oturumu.

        Dönüş:
            Optional[Dict[str, Any]]: Optimizasyon önerisi.
        """
        metrics = session.query(GenerationMetrics).all()

        cache_metrics = {True: [], False: []}
        for m in metrics:
            if m.generation_params and 'cache_enabled' in m.generation_params:
                cache = m.generation_params['cache_enabled']
                cache_metrics[cache].append(
                    m.execution_time_ms or 0
                )

        if not cache_metrics[True] and not cache_metrics[False]:
            return None

        cache_enabled_avg = (
            statistics.mean(cache_metrics[True])
            if cache_metrics[True]
            else float('inf')
        )
        cache_disabled_avg = (
            statistics.mean(cache_metrics[False])
            if cache_metrics[False]
            else float('inf')
        )

        cache_enabled = cache_enabled_avg < cache_disabled_avg

        optimization = {
            'parameter': 'cache_strategy',
            'recommended_value': 'enabled' if cache_enabled else 'disabled',
            'optimization_type': OptimizationType.PERFORMANCE,
            'rationale': 'Ortalama işlem süresine göre optimize edildi',
        }

        logger.debug("Önbellek stratejisi optimize edildi: %s",
                     'etkin' if cache_enabled else 'devre dışı')
        return optimization

    def _optimize_rule_weights(self, session: Session) -> Optional[Dict[str, Any]]:
        """
        Kural ağırlıklarını optimize eder.

        Argümanlar:
            session: Veritabanı oturumu.

        Dönüş:
            Optional[Dict[str, Any]]: Optimizasyon önerisi.
        """
        feedbacks = session.query(LearningFeedback).all()

        if not feedbacks:
            return None

        rule_related_feedbacks = [
            f for f in feedbacks
            if f.aspects and 'rule_quality' in f.aspects
        ]

        if not rule_related_feedbacks:
            return None

        avg_rule_quality = statistics.mean(
            [f.aspects['rule_quality'] for f in rule_related_feedbacks
             if isinstance(f.aspects.get('rule_quality'), (int, float))]
        )

        weight_adjustment = max(0.5, min(2.0, avg_rule_quality / 0.5))

        optimization = {
            'parameter': 'rule_weights',
            'recommended_value': weight_adjustment,
            'optimization_type': OptimizationType.QUALITY,
            'rationale': 'Geri bildirim kalitesi analiz edilerek ayarlandı',
        }

        logger.debug("Kural ağırlıkları optimize edildi: %.2f", weight_adjustment)
        return optimization

    def _optimize_generation_params(
        self, session: Session
    ) -> Optional[Dict[str, Any]]:
        """
        Üretim parametrelerini optimize eder.

        Argümanlar:
            session: Veritabanı oturumu.

        Dönüş:
            Optional[Dict[str, Any]]: Optimizasyon önerisi.
        """
        metrics = session.query(GenerationMetrics).all()

        if not metrics:
            return None

        best_metric = max(
            metrics,
            key=lambda m: m.quality_score or 0
        )

        if not best_metric or not best_metric.generation_params:
            return None

        optimization = {
            'parameter': 'generation_params',
            'recommended_value': best_metric.generation_params,
            'optimization_type': OptimizationType.QUALITY,
            'rationale': 'En yüksek kalite puanını üreten parametreler',
        }

        logger.debug("Üretim parametreleri optimize edildi")
        return optimization

    def apply_optimization(
        self, session: Session, optimization: Dict[str, Any]
    ) -> OptimizationHistory:
        """
        Bir optimizasyonu uygular ve kaydeder.

        Argümanlar:
            session: Veritabanı oturumu.
            optimization: Uygulanacak optimizasyon.

        Dönüş:
            OptimizationHistory: Kaydedilen optimizasyon.
        """
        logger.info("Optimizasyon uygulanıyor: %s", optimization.get('parameter'))

        opt_record = OptimizationHistory(
            parameter=optimization.get('parameter'),
            recommended_value=optimization.get('recommended_value'),
            optimization_type=optimization.get('optimization_type'),
            rationale=optimization.get('rationale'),
        )

        session.add(opt_record)
        session.commit()

        logger.debug("Optimizasyon kaydedildi, ID: %s", opt_record.id)
        return opt_record


class RuleRecommender:
    """
    Veri sütunları için kural önerileri sunar.
    """

    def recommend_rules(
        self, session: Session, column_profiles: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Sütun profilleri bazında kural önerileri verir.

        Argümanlar:
            session: Veritabanı oturumu.
            column_profiles: Sütun profillerinin listesi.
                Her profil: {
                    'name': str,
                    'data_type': str,
                    'sample_values': list,
                    'null_rate': float,
                }

        Dönüş:
            List[Dict[str, Any]]: Kural önerileri.
        """
        logger.info("Kural önerileri oluşturuluyor: %d sütun", len(column_profiles))

        recommendations = []

        for column in column_profiles:
            col_name = column.get('name')
            col_type = column.get('data_type')

            similar_patterns = self._find_similar_columns(
                session, col_name, col_type
            )

            if similar_patterns:
                ranked = self._rank_recommendations(similar_patterns)

                for rank, pattern in enumerate(ranked[:3], 1):
                    rec = {
                        'column_name': col_name,
                        'column_type': col_type,
                        'recommended_rule': pattern.get('rule'),
                        'confidence': pattern.get('confidence'),
                        'rank': rank,
                    }
                    recommendations.append(rec)

        logger.info("Kural önerileri hazırlandı: %d", len(recommendations))
        return recommendations

    def _find_similar_columns(
        self, session: Session, column_name: str, data_type: str
    ) -> List[Dict[str, Any]]:
        """
        Geçmiş verilerden benzer sütunları bulur.

        Argümanlar:
            session: Veritabanı oturumu.
            column_name: Sütun adı.
            data_type: Veri türü.

        Dönüş:
            List[Dict[str, Any]]: Benzer sütun örüntüleri.
        """
        patterns = session.query(LearnedPattern).filter(
            LearnedPattern.pattern_type == PatternType.COLUMN_MAPPING
        ).all()

        similar = []
        for pattern in patterns:
            if pattern.pattern_data:
                strategy = pattern.pattern_data.get('strategy')
                if strategy:
                    similar.append({
                        'rule': strategy,
                        'confidence': pattern.confidence,
                    })

        logger.debug("Benzer sütunlar bulundu: %d adet", len(similar))
        return similar

    def _rank_recommendations(
        self, recommendations: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Önerileri güven puanına göre sıralar.

        Argümanlar:
            recommendations: Sıralanacak öneriler.

        Dönüş:
            List[Dict[str, Any]]: Sıralanmış öneriler.
        """
        ranked = sorted(
            recommendations,
            key=lambda x: x.get('confidence', 0),
            reverse=True
        )

        logger.debug("Öneriler sıralandı: %d", len(ranked))
        return ranked


class ModelWeightAdjuster:
    """
    Sistem modellerinin ağırlıklarını geri bildirimlere göre ayarlar.
    """

    def __init__(self):
        """Ağırlık ayarlayıcısını başlatır."""
        self._current_weights = self._get_default_weights()

    def _get_default_weights(self) -> Dict[str, Dict[str, float]]:
        """
        Varsayılan ağırlıkları döndürür.

        Dönüş:
            Dict[str, Dict[str, float]]: Varsayılan ağırlıklar.
        """
        return {
            'column_classifier': {
                'type_accuracy': 1.0,
                'pii_detection': 1.0,
                'pattern_matching': 1.0,
            },
            'rule_engine': {
                'rule_coverage': 1.0,
                'constraint_satisfaction': 1.0,
                'performance': 1.0,
            },
        }

    def adjust_weights(self, session: Session) -> Dict[str, Dict[str, float]]:
        """
        Geri bildirim verilerine göre ağırlıkları ayarlar.

        Argümanlar:
            session: Veritabanı oturumu.

        Dönüş:
            Dict[str, Dict[str, float]]: Ayarlanmış ağırlıklar.
        """
        logger.info("Ağırlıklar ayarlanıyor")

        classifier_weights = self._calculate_column_classifier_weights(session)
        rule_weights = self._calculate_rule_engine_weights(session)

        self._current_weights['column_classifier'] = classifier_weights
        self._current_weights['rule_engine'] = rule_weights

        logger.debug("Ağırlıklar ayarlandı: %s", self._current_weights)
        return self._current_weights

    def _calculate_column_classifier_weights(
        self, session: Session
    ) -> Dict[str, float]:
        """
        Sütun sınıflandırıcı ağırlıklarını hesaplar.

        Argümanlar:
            session: Veritabanı oturumu.

        Dönüş:
            Dict[str, float]: Ayarlanmış ağırlıklar.
        """
        feedbacks = session.query(LearningFeedback).all()

        weights = {
            'type_accuracy': 1.0,
            'pii_detection': 1.0,
            'pattern_matching': 1.0,
        }

        if feedbacks:
            classifier_feedback = [
                f for f in feedbacks
                if f.aspects and 'classifier_quality' in f.aspects
            ]

            if classifier_feedback:
                avg_quality = statistics.mean(
                    [f.aspects['classifier_quality']
                     for f in classifier_feedback
                     if isinstance(f.aspects.get('classifier_quality'),
                                  (int, float))]
                )
                adjustment = avg_quality / 0.5

                weights = {
                    k: v * adjustment
                    for k, v in weights.items()
                }

        logger.debug("Sınıflandırıcı ağırlıkları hesaplandı: %s", weights)
        return weights

    def _calculate_rule_engine_weights(
        self, session: Session
    ) -> Dict[str, float]:
        """
        Kural motoru ağırlıklarını hesaplar.

        Argümanlar:
            session: Veritabanı oturumu.

        Dönüş:
            Dict[str, float]: Ayarlanmış ağırlıklar.
        """
        feedbacks = session.query(LearningFeedback).all()

        weights = {
            'rule_coverage': 1.0,
            'constraint_satisfaction': 1.0,
            'performance': 1.0,
        }

        if feedbacks:
            rule_feedback = [
                f for f in feedbacks
                if f.aspects and 'rule_quality' in f.aspects
            ]

            if rule_feedback:
                avg_quality = statistics.mean(
                    [f.aspects['rule_quality']
                     for f in rule_feedback
                     if isinstance(f.aspects.get('rule_quality'),
                                  (int, float))]
                )
                adjustment = avg_quality / 0.5

                weights = {
                    k: v * adjustment
                    for k, v in weights.items()
                }

        logger.debug("Kural motoru ağırlıkları hesaplandı: %s", weights)
        return weights

    def get_current_weights(self) -> Dict[str, Dict[str, float]]:
        """
        Şu anki ağırlıkları döndürür.

        Dönüş:
            Dict[str, Dict[str, float]]: Mevcut ağırlıklar.
        """
        return self._current_weights.copy()

    def reset_weights(self) -> Dict[str, Dict[str, float]]:
        """
        Ağırlıkları varsayılan değerlere sıfırlar.

        Dönüş:
            Dict[str, Dict[str, float]]: Sıfırlanmış ağırlıklar.
        """
        logger.warning("Ağırlıklar varsayılan değerlere sıfırlanıyor")
        self._current_weights = self._get_default_weights()
        return self._current_weights


def get_self_learning_engine() -> SelfLearningEngine:
    """
    Kendi kendini öğrenen motor örneğini döndürür.

    Dönüş:
        SelfLearningEngine: Başlatılmış motor.
    """
    return SelfLearningEngine()
