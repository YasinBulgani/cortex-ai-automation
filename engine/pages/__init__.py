"""
Pages paketi — Page Object Model sınıfları
"""
from .base_page import BasePage
from .login_page import LoginPage
from .dashboard_page import DashboardPage
from .projects_page import ProjectsPage
from .scenarios_page import ScenariosListPage, ScenarioFormPage
from .flows_page import FlowsPage, FlowEditorPage
from .executions_page import ExecutionsListPage, NewExecutionPage
from .approvals_page import ApprovalsPage
from .regression_page import RegressionPage
from .import_page import ImportPage
from .common_nav import CommonNav

__all__ = [
    "BasePage",
    "LoginPage",
    "DashboardPage",
    "ProjectsPage",
    "ScenariosListPage",
    "ScenarioFormPage",
    "FlowsPage",
    "FlowEditorPage",
    "ExecutionsListPage",
    "NewExecutionPage",
    "ApprovalsPage",
    "RegressionPage",
    "ImportPage",
    "CommonNav",
]
