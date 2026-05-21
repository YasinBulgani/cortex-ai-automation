"""
Visual AI Service
AI-powered visual comparison, anomaly detection, and baseline management
"""

import os
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import numpy as np
from PIL import Image
import json
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class VisualAnomaly:
    """Visual anomaly detected in image comparison"""
    type: str  # color_shift, layout_change, missing_element, etc.
    location: Tuple[int, int, int, int]  # x, y, width, height
    severity: str  # critical, high, medium, low
    confidence: float  # 0-1
    description: str


@dataclass
class VisualAnalysis:
    """Complete visual analysis results"""
    similarity: float
    anomalies: List[VisualAnomaly]
    has_anomalies: bool
    recommendations: List[str]
    should_update_baseline: bool


class VisualAIAnalyzer:
    """AI-powered visual analysis using ML techniques"""

    def __init__(self):
        self.anomaly_detection_threshold = 0.80
        self.color_shift_threshold = 30  # RGB value difference
        self.layout_change_threshold = 0.15  # % difference
        logger.info("Visual AI Analyzer initialized")

    def analyze_visual_difference(
        self,
        current_image_path: str,
        baseline_image_path: str,
        baseline_name: str = "unknown"
    ) -> VisualAnalysis:
        """
        Perform comprehensive visual analysis

        Args:
            current_image_path: Path to current screenshot
            baseline_image_path: Path to baseline screenshot
            baseline_name: Name of the baseline for reference

        Returns:
            Complete visual analysis with anomalies and recommendations
        """
        try:
            # Load images
            current_img = Image.open(current_image_path)
            baseline_img = Image.open(baseline_image_path)

            # Convert to RGB
            if current_img.mode != 'RGB':
                current_img = current_img.convert('RGB')
            if baseline_img.mode != 'RGB':
                baseline_img = baseline_img.convert('RGB')

            # Resize to match
            if current_img.size != baseline_img.size:
                baseline_img = baseline_img.resize(current_img.size, Image.Resampling.LANCZOS)

            # Calculate similarity
            similarity = self._calculate_perceptual_similarity(current_img, baseline_img)

            # Detect anomalies
            anomalies = self._detect_anomalies(current_img, baseline_img, similarity)

            # Generate recommendations
            recommendations = self._generate_recommendations(anomalies, similarity)

            # Determine if baseline should be updated
            should_update = self._should_update_baseline(similarity, anomalies, len(anomalies))

            logger.info(f"Visual analysis complete for {baseline_name}", {
                "similarity": f"{similarity:.2%}",
                "anomalies": len(anomalies),
                "update_recommended": should_update,
            })

            return VisualAnalysis(
                similarity=similarity,
                anomalies=anomalies,
                has_anomalies=len(anomalies) > 0,
                recommendations=recommendations,
                should_update_baseline=should_update,
            )

        except Exception as e:
            logger.error(f"Visual analysis failed for {baseline_name}: {e}")
            return VisualAnalysis(
                similarity=0,
                anomalies=[],
                has_anomalies=False,
                recommendations=[f"Error during analysis: {str(e)}"],
                should_update_baseline=False,
            )

    def _calculate_perceptual_similarity(
        self,
        img1: Image.Image,
        img2: Image.Image
    ) -> float:
        """Calculate perceptual similarity between images using MSE and structural similarity"""
        # Convert to numpy arrays
        arr1 = np.array(img1).astype(float) / 255.0
        arr2 = np.array(img2).astype(float) / 255.0

        # Mean Squared Error
        mse = np.mean((arr1 - arr2) ** 2)
        mse_similarity = max(0, 1 - (mse * 4))  # Scale MSE to 0-1 range

        # Structural Similarity (simplified)
        ssim = self._calculate_ssim(arr1, arr2)

        # Combined score (weighted average)
        similarity = 0.6 * ssim + 0.4 * mse_similarity

        return max(0, min(1, similarity))

    def _calculate_ssim(self, img1: np.ndarray, img2: np.ndarray) -> float:
        """Calculate Structural Similarity Index (SSIM)"""
        # Convert to grayscale
        gray1 = np.mean(img1, axis=2)
        gray2 = np.mean(img2, axis=2)

        # SSIM constants
        C1 = 0.01 ** 2
        C2 = 0.03 ** 2

        # Mean
        mean1 = gray1.mean()
        mean2 = gray2.mean()

        # Variance and covariance
        var1 = gray1.var()
        var2 = gray2.var()
        cov = np.mean((gray1 - mean1) * (gray2 - mean2))

        # SSIM calculation
        numerator = (2 * mean1 * mean2 + C1) * (2 * cov + C2)
        denominator = (mean1 ** 2 + mean2 ** 2 + C1) * (var1 + var2 + C2)

        ssim = numerator / denominator if denominator > 0 else 0
        return max(0, min(1, ssim))

    def _detect_anomalies(
        self,
        current_img: Image.Image,
        baseline_img: Image.Image,
        similarity: float
    ) -> List[VisualAnomaly]:
        """Detect visual anomalies"""
        anomalies = []

        if similarity < self.anomaly_detection_threshold:
            # Detect color shifts
            color_anomalies = self._detect_color_shifts(current_img, baseline_img)
            anomalies.extend(color_anomalies)

            # Detect layout changes
            layout_anomalies = self._detect_layout_changes(current_img, baseline_img)
            anomalies.extend(layout_anomalies)

            # Detect missing elements
            missing_anomalies = self._detect_missing_elements(current_img, baseline_img)
            anomalies.extend(missing_anomalies)

        return sorted(anomalies, key=lambda x: x.severity, reverse=True)

    def _detect_color_shifts(
        self,
        current_img: Image.Image,
        baseline_img: Image.Image
    ) -> List[VisualAnomaly]:
        """Detect significant color shifts"""
        anomalies = []

        curr_arr = np.array(current_img).astype(int)
        base_arr = np.array(baseline_img).astype(int)

        # Calculate color difference
        color_diff = np.abs(curr_arr.astype(int) - base_arr.astype(int))
        avg_color_diff = np.mean(color_diff)

        if avg_color_diff > self.color_shift_threshold:
            # Find regions with biggest color shifts
            max_diff_per_pixel = np.max(color_diff, axis=2)
            high_diff_mask = max_diff_per_pixel > self.color_shift_threshold

            if np.any(high_diff_mask):
                # Find bounding box of color shifts
                rows, cols = np.where(high_diff_mask)
                if len(rows) > 0:
                    x, y = cols.min(), rows.min()
                    w, h = cols.max() - x, rows.max() - y

                    severity = "critical" if avg_color_diff > 100 else "high"
                    confidence = min(1.0, avg_color_diff / 255.0)

                    anomalies.append(VisualAnomaly(
                        type="color_shift",
                        location=(int(x), int(y), int(w), int(h)),
                        severity=severity,
                        confidence=confidence,
                        description=f"Color shift detected (avg diff: {avg_color_diff:.0f})"
                    ))

        return anomalies

    def _detect_layout_changes(
        self,
        current_img: Image.Image,
        baseline_img: Image.Image
    ) -> List[VisualAnomaly]:
        """Detect layout and positioning changes"""
        anomalies = []

        # Simple layout detection using edge detection
        curr_arr = np.array(current_img.convert('L')).astype(float) / 255.0
        base_arr = np.array(baseline_img.convert('L')).astype(float) / 255.0

        # Calculate difference
        layout_diff = np.abs(curr_arr - base_arr)
        layout_change_ratio = np.sum(layout_diff > 0.1) / layout_diff.size

        if layout_change_ratio > self.layout_change_threshold:
            severity = "critical" if layout_change_ratio > 0.30 else "high"

            anomalies.append(VisualAnomaly(
                type="layout_change",
                location=(0, 0, int(current_img.width), int(current_img.height)),
                severity=severity,
                confidence=min(1.0, layout_change_ratio),
                description=f"Layout change detected ({layout_change_ratio:.1%} of pixels affected)"
            ))

        return anomalies

    def _detect_missing_elements(
        self,
        current_img: Image.Image,
        baseline_img: Image.Image
    ) -> List[VisualAnomaly]:
        """Detect missing or hidden elements"""
        anomalies = []

        curr_arr = np.array(current_img.convert('L')).astype(float) / 255.0
        base_arr = np.array(baseline_img.convert('L')).astype(float) / 255.0

        # Areas that were dark in baseline but light in current (possible hiding)
        hidden_mask = (base_arr < 0.3) & (curr_arr > 0.7)

        if np.any(hidden_mask):
            rows, cols = np.where(hidden_mask)
            if len(rows) > 10:  # Only report if significant
                x, y = cols.min(), rows.min()
                w, h = cols.max() - x, rows.max() - y
                ratio = np.sum(hidden_mask) / hidden_mask.size

                anomalies.append(VisualAnomaly(
                    type="element_visibility_change",
                    location=(int(x), int(y), int(w), int(h)),
                    severity="high" if ratio > 0.05 else "medium",
                    confidence=min(1.0, ratio),
                    description=f"Element visibility change detected ({ratio:.1%})"
                ))

        return anomalies

    def _generate_recommendations(
        self,
        anomalies: List[VisualAnomaly],
        similarity: float
    ) -> List[str]:
        """Generate recommendations based on anomalies"""
        recommendations = []

        if not anomalies:
            if similarity > 0.95:
                recommendations.append("✓ Visual match is excellent")
            elif similarity > 0.85:
                recommendations.append("✓ Visual match is good")
            else:
                recommendations.append("Consider updating baseline if changes are intentional")
            return recommendations

        # Analyze anomalies
        anomaly_types = {}
        for anomaly in anomalies:
            if anomaly.type not in anomaly_types:
                anomaly_types[anomaly.type] = []
            anomaly_types[anomaly.type].append(anomaly)

        # Generate specific recommendations
        if "color_shift" in anomaly_types:
            color_anomalies = anomaly_types["color_shift"]
            if any(a.severity == "critical" for a in color_anomalies):
                recommendations.append(
                    "Critical color shift detected - investigate CSS or theme changes"
                )
            else:
                recommendations.append("Minor color shift detected - may be due to rendering differences")

        if "layout_change" in anomaly_types:
            recommendations.append(
                "Layout change detected - check CSS, viewport, or element positioning"
            )

        if "element_visibility_change" in anomaly_types:
            recommendations.append(
                "Element visibility change detected - check display, opacity, or z-index CSS"
            )

        if len(anomalies) > 3:
            recommendations.append("Multiple anomalies detected - consider full page review")

        if similarity < 0.7:
            recommendations.append("Large visual difference - recommend thorough investigation")

        return recommendations

    def _should_update_baseline(
        self,
        similarity: float,
        anomalies: List[VisualAnomaly],
        anomaly_count: int
    ) -> bool:
        """Determine if baseline should be automatically updated"""
        # Update only if:
        # 1. No critical anomalies
        # 2. Similarity is still reasonable (> 0.75)
        # 3. Few anomalies (< 2)

        has_critical = any(a.severity == "critical" for a in anomalies)
        if has_critical:
            return False

        if similarity < 0.75:
            return False

        if anomaly_count > 1:
            return False

        return True

    def generate_analysis_report(self, analysis: VisualAnalysis, baseline_name: str) -> str:
        """Generate human-readable analysis report"""
        report = f"""
# Visual Analysis Report: {baseline_name}

## Summary
- **Similarity**: {analysis.similarity:.1%}
- **Anomalies Detected**: {len(analysis.anomalies)}
- **Has Critical Issues**: {"Yes" if analysis.has_anomalies else "No"}
- **Update Baseline Recommended**: {"Yes" if analysis.should_update_baseline else "No"}

## Anomalies
"""
        if analysis.anomalies:
            for i, anomaly in enumerate(analysis.anomalies, 1):
                report += f"""
### Anomaly {i}
- **Type**: {anomaly.type}
- **Severity**: {anomaly.severity}
- **Confidence**: {anomaly.confidence:.1%}
- **Location**: x={anomaly.location[0]}, y={anomaly.location[1]}, w={anomaly.location[2]}, h={anomaly.location[3]}
- **Description**: {anomaly.description}
"""
        else:
            report += "\nNo anomalies detected.\n"

        report += "\n## Recommendations\n"
        for rec in analysis.recommendations:
            report += f"- {rec}\n"

        return report


class SmartBaselineManager:
    """Intelligent baseline management with AI decision making"""

    def __init__(self, baselines_dir: str):
        self.baselines_dir = baselines_dir
        self.analyzer = VisualAIAnalyzer()
        self.baseline_metadata = self._load_metadata()

    def _load_metadata(self) -> Dict[str, Any]:
        """Load baseline metadata"""
        metadata_file = os.path.join(self.baselines_dir, "baseline_metadata.json")
        if os.path.exists(metadata_file):
            with open(metadata_file, 'r') as f:
                return json.load(f)
        return {}

    def _save_metadata(self) -> None:
        """Save baseline metadata"""
        metadata_file = os.path.join(self.baselines_dir, "baseline_metadata.json")
        with open(metadata_file, 'w') as f:
            json.dump(self.baseline_metadata, f, indent=2)

    def smart_update_baseline(
        self,
        baseline_name: str,
        current_image_path: str,
        baseline_image_path: str,
        force: bool = False
    ) -> Dict[str, Any]:
        """
        Intelligently decide whether to update baseline

        Args:
            baseline_name: Name of the baseline
            current_image_path: Path to current screenshot
            baseline_image_path: Path to baseline screenshot
            force: Force update regardless of analysis

        Returns:
            Dictionary with update decision and analysis
        """
        # Perform analysis
        analysis = self.analyzer.analyze_visual_difference(
            current_image_path,
            baseline_image_path,
            baseline_name
        )

        # Decide on update
        should_update = force or analysis.should_update_baseline

        # Update metadata
        if baseline_name not in self.baseline_metadata:
            self.baseline_metadata[baseline_name] = {}

        self.baseline_metadata[baseline_name].update({
            "last_checked": str(Path(baseline_image_path).stat().st_mtime),
            "last_similarity": analysis.similarity,
            "last_update": str(Path(baseline_image_path).stat().st_mtime) if should_update else self.baseline_metadata[baseline_name].get("last_update"),
            "anomalies": len(analysis.anomalies),
            "update_count": self.baseline_metadata[baseline_name].get("update_count", 0) + (1 if should_update else 0),
        })

        self._save_metadata()

        return {
            "baseline_name": baseline_name,
            "should_update": should_update,
            "similarity": analysis.similarity,
            "anomalies": len(analysis.anomalies),
            "reasons": analysis.recommendations,
        }

    def get_baseline_status(self, baseline_name: str) -> Dict[str, Any]:
        """Get status of a baseline"""
        if baseline_name not in self.baseline_metadata:
            return {"exists": False}

        metadata = self.baseline_metadata[baseline_name]
        return {
            "exists": True,
            "similarity": metadata.get("last_similarity", "unknown"),
            "anomalies": metadata.get("anomalies", 0),
            "update_count": metadata.get("update_count", 0),
        }


# Singleton instance
_analyzer: Optional[VisualAIAnalyzer] = None


def get_visual_ai_analyzer() -> VisualAIAnalyzer:
    """Get or create visual AI analyzer instance"""
    global _analyzer
    if _analyzer is None:
        _analyzer = VisualAIAnalyzer()
    return _analyzer


def reset_visual_ai_analyzer() -> None:
    """Reset analyzer instance"""
    global _analyzer
    _analyzer = None
