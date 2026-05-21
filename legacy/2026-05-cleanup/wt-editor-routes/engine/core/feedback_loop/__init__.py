"""Feedback Loop — Self-learning test execution feedback sistemi."""
from core.feedback_loop.collector import ResultCollector
from core.feedback_loop.analyzer import PatternAnalyzer
from core.feedback_loop.optimizer import SuiteOptimizer

__all__ = ["ResultCollector", "PatternAnalyzer", "SuiteOptimizer"]
