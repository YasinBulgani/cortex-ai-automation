"""
Scheduler — CI/CD Entegrasyonu ve Test Zamanlama

Cron-tabanlı test zamanlaması ve CI/CD pipeline
yapılandırması üretir (GitHub Actions, Jenkins, GitLab CI).
"""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional


class CIPlatform(str, Enum):
    GITHUB_ACTIONS = "github_actions"
    JENKINS = "jenkins"
    GITLAB_CI = "gitlab_ci"
    AZURE_DEVOPS = "azure_devops"


@dataclass
class ScheduleConfig:
    name: str
    cron_expression: str
    platform: CIPlatform
    pipeline_yaml: str
    trigger_events: List[str]
    description: str


class Scheduler:
    """Test suitelerini CI/CD platformlarına entegre eden zamanlayıcı."""

    # Yaygın cron ifadeleri
    CRON_PRESETS = {
        "hourly": "0 * * * *",
        "daily_midnight": "0 0 * * *",
        "daily_morning": "0 9 * * *",
        "weekly_monday": "0 9 * * 1",
        "on_commit": "push",
        "on_pr": "pull_request",
    }

    def create_schedule(
        self,
        suite_name: str,
        platform: CIPlatform,
        frequency: str = "daily_morning",
        test_command: str = "pytest tests/ -v",
    ) -> ScheduleConfig:
        """
        CI/CD pipeline yapılandırması üretir.

        Args:
            suite_name: Test suite adı
            platform: CI platformu
            frequency: Zamanlama sıklığı (CRON_PRESETS anahtarı veya cron ifadesi)
            test_command: Çalıştırılacak komut

        Returns:
            ScheduleConfig
        """
        cron = self.CRON_PRESETS.get(frequency, frequency)
        generators = {
            CIPlatform.GITHUB_ACTIONS: self._github_actions_yaml,
            CIPlatform.JENKINS: self._jenkins_pipeline,
            CIPlatform.GITLAB_CI: self._gitlab_ci_yaml,
            CIPlatform.AZURE_DEVOPS: self._azure_devops_yaml,
        }
        gen_fn = generators.get(platform, self._github_actions_yaml)
        yaml_content = gen_fn(suite_name, cron, test_command)

        return ScheduleConfig(
            name=suite_name,
            cron_expression=cron,
            platform=platform,
            pipeline_yaml=yaml_content,
            trigger_events=["push", "pull_request", "schedule"],
            description=f"{suite_name} — {platform.value} ile {frequency} çalıştırma",
        )

    def _github_actions_yaml(self, name: str, cron: str, cmd: str) -> str:
        safe_name = name.replace(" ", "-").lower()
        cron_section = f'    - cron: "{cron}"' if not cron.startswith(("push", "pull")) else ""
        return f"""name: {name}

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]
  schedule:
{cron_section if cron_section else '    - cron: "0 9 * * 1"'}

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Python Kurulumu
        uses: actions/setup-python@v4
        with:
          python-version: "3.11"
      - name: Bağımlılıkları Kur
        run: pip install -r requirements.txt
      - name: Testleri Çalıştır
        run: {cmd}
      - name: Test Raporunu Yükle
        uses: actions/upload-artifact@v3
        if: always()
        with:
          name: test-results
          path: reports/
"""

    def _jenkins_pipeline(self, name: str, cron: str, cmd: str) -> str:
        return f"""pipeline {{
    agent any
    triggers {{
        cron('{cron}')
    }}
    stages {{
        stage('Checkout') {{
            steps {{ checkout scm }}
        }}
        stage('Install') {{
            steps {{ sh 'pip install -r requirements.txt' }}
        }}
        stage('Test: {name}') {{
            steps {{ sh '{cmd}' }}
        }}
        stage('Rapor') {{
            steps {{ junit 'reports/*.xml' }}
        }}
    }}
    post {{
        always {{ archiveArtifacts artifacts: 'reports/**/*', allowEmptyArchive: true }}
        failure {{ emailext to: 'team@bank.com', subject: 'Test Başarısız: {name}' }}
    }}
}}
"""

    def _gitlab_ci_yaml(self, name: str, cron: str, cmd: str) -> str:
        return f"""stages:
  - test
  - report

{name.lower().replace(' ', '_')}:
  stage: test
  image: python:3.11
  before_script:
    - pip install -r requirements.txt
  script:
    - {cmd}
  artifacts:
    reports:
      junit: reports/*.xml
    when: always
  rules:
    - if: $CI_PIPELINE_SOURCE == "schedule"
    - if: $CI_COMMIT_BRANCH == "main"
"""

    def _azure_devops_yaml(self, name: str, cron: str, cmd: str) -> str:
        return f"""trigger:
  branches:
    include: [main, develop]

schedules:
  - cron: "{cron}"
    displayName: Scheduled {name}
    branches:
      include: [main]

pool:
  vmImage: ubuntu-latest

steps:
  - task: UsePythonVersion@0
    inputs:
      versionSpec: "3.11"
  - script: pip install -r requirements.txt
    displayName: Bağımlılık Kurulumu
  - script: {cmd}
    displayName: {name}
  - task: PublishTestResults@2
    inputs:
      testResultsFiles: reports/*.xml
    condition: always()
"""
