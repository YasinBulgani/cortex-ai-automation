"""
AI Test Automation Platform — Servis Paketi

Bu paket, otomatik test üretimi ve yönetimi için gerekli
tüm servisleri içerir.
"""

from app.services.test_platform.document_analyzer import DocumentAnalyzer
from app.services.test_platform.test_generator import TestGenerator
from app.services.test_platform.classification_engine import ClassificationEngine
from app.services.test_platform.test_data_engine import TestDataEngine
from app.services.test_platform.automation_generator import AutomationGenerator
from app.services.test_platform.locator_engine import LocatorEngine
from app.services.test_platform.dry_run_validator import DryRunValidator
from app.services.test_platform.execution_engine import ExecutionEngine
from app.services.test_platform.scheduler import Scheduler
from app.services.test_platform.report_generator import ReportGenerator
from app.services.test_platform.bug_drafter import BugDrafter
from app.services.test_platform.learning_engine import LearningEngine

__all__ = [
    "DocumentAnalyzer",
    "TestGenerator",
    "ClassificationEngine",
    "TestDataEngine",
    "AutomationGenerator",
    "LocatorEngine",
    "DryRunValidator",
    "ExecutionEngine",
    "Scheduler",
    "ReportGenerator",
    "BugDrafter",
    "LearningEngine",
]
