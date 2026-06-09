# Karate API Test CI/CD Integration Guide

Integration patterns for continuous integration and deployment pipelines.

## GitHub Actions

### Basic Setup

Create `.github/workflows/api-tests.yml`:

```yaml
name: API Tests - Karate

on:
  push:
    branches: [main, develop, feature/**]
    paths:
      - 'backend/**'
      - '.github/workflows/api-tests.yml'
  pull_request:
    branches: [main, develop]
    paths:
      - 'backend/**'

concurrency:
  group: api-tests-${{ github.ref }}
  cancel-in-progress: true

jobs:
  test:
    name: Karate API Tests
    runs-on: ubuntu-latest
    timeout-minutes: 15

    services:
      postgres:
        image: postgres:14-alpine
        env:
          POSTGRES_USER: neurex
          POSTGRES_PASSWORD: neurex_test
          POSTGRES_DB: neurex_test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432

      redis:
        image: redis:7-alpine
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 6379:6379

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Java
        uses: actions/setup-java@v4
        with:
          java-version: '11'
          distribution: 'temurin'
          cache: maven

      - name: Wait for PostgreSQL
        run: |
          until pg_isready -h localhost -p 5432 -U neurex; do
            echo "Waiting for PostgreSQL..."
            sleep 1
          done

      - name: Run DB migrations
        working-directory: backend
        env:
          DATABASE_URL: postgresql://neurex:neurex_test@localhost:5432/neurex_test
        run: |
          pip install alembic sqlalchemy psycopg2-binary
          alembic upgrade head

      - name: Seed test data
        working-directory: backend
        env:
          DATABASE_URL: postgresql://neurex:neurex_test@localhost:5432/neurex_test
        run: |
          python scripts/seed_test_users.py

      - name: Start FastAPI backend
        working-directory: backend
        env:
          DATABASE_URL: postgresql://neurex:neurex_test@localhost:5432/neurex_test
          REDIS_URL: redis://localhost:6379/0
          SECRET_KEY: test-secret-key-1234567890
          JWT_SECRET: test-jwt-secret
        run: |
          pip install -e .
          uvicorn app.main:app --host 0.0.0.0 --port 8000 &
          sleep 5

      - name: Run Karate tests
        working-directory: backend
        run: |
          mvn clean test \
            -Dtest=karate.TestRunner \
            -Dbase.url=http://localhost:8000 \
            -Dkarate.threads=5 \
            -Dkarate.options="--format html"

      - name: Upload test results
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: karate-report-${{ github.run_id }}
          path: |
            backend/target/karate-reports/
            backend/target/surefire-reports/
          retention-days: 30

      - name: Publish test results
        if: always()
        uses: EnricoMi/publish-unit-test-result-action@v2
        with:
          files: backend/target/surefire-reports/**/*.xml
          check_name: Karate API Test Results

      - name: Comment PR with test results
        if: github.event_name == 'pull_request' && always()
        uses: actions/github-script@v7
        with:
          script: |
            const fs = require('fs');
            const report = fs.readFileSync('backend/target/karate-reports/karate-summary.txt', 'utf8');
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: `## API Test Results\n\`\`\`\n${report}\n\`\`\``
            });
```

### Advanced: Multi-Environment Testing

```yaml
name: API Tests - Multi-Environment

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        environment: [dev, stage]
        java-version: [11, 17]
    
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-java@v4
        with:
          java-version: ${{ matrix.java-version }}
          cache: maven

      - name: Run tests for ${{ matrix.environment }}
        working-directory: backend
        env:
          API_URL: ${{ secrets[format('API_URL_{0}', matrix.environment)] }}
        run: |
          mvn test -Dtest=karate.TestRunner \
            -Dbase.url=${{ env.API_URL }} \
            -Dkarate.env=${{ matrix.environment }}
```

## Jenkins Pipeline

### Declarative Pipeline

```groovy
pipeline {
  agent {
    docker {
      image 'maven:3.9-eclipse-temurin-11'
      args '-v /root/.m2:/root/.m2'
    }
  }

  options {
    buildDiscarder(logRotator(numToKeepStr: '30'))
    timeout(time: 15, unit: 'MINUTES')
    timestamps()
  }

  stages {
    stage('Setup') {
      steps {
        sh '''
          echo "Starting PostgreSQL and Redis..."
          docker run -d --name postgres -e POSTGRES_PASSWORD=test postgres:14
          docker run -d --name redis redis:7
          sleep 5
        '''
      }
    }

    stage('Migrate') {
      steps {
        dir('backend') {
          sh '''
            pip install alembic sqlalchemy psycopg2-binary
            alembic upgrade head
            python scripts/seed_test_users.py
          '''
        }
      }
    }

    stage('Start Backend') {
      steps {
        dir('backend') {
          sh '''
            pip install -e .
            nohup uvicorn app.main:app --port 8000 &
            sleep 5
          '''
        }
      }
    }

    stage('Run Karate Tests') {
      steps {
        dir('backend') {
          sh '''
            mvn clean test \
              -Dtest=karate.TestRunner \
              -Dbase.url=http://localhost:8000 \
              -Dkarate.threads=5
          '''
        }
      }
    }

    stage('Generate Report') {
      steps {
        sh '''
          mkdir -p reports
          cp backend/target/karate-reports/* reports/ || true
        '''
      }
    }
  }

  post {
    always {
      junit 'backend/target/surefire-reports/**/*.xml'
      
      publishHTML([
        reportDir: 'reports',
        reportFiles: 'karate-summary.html',
        reportName: 'Karate API Test Report',
        keepAll: true
      ])

      sh '''
        docker rm -f postgres redis || true
      '''
    }

    success {
      echo 'All API tests passed!'
    }

    failure {
      echo 'API tests failed!'
      emailext(
        subject: "API Tests Failed: ${env.JOB_NAME} #${env.BUILD_NUMBER}",
        body: "Check console output at ${env.BUILD_URL}",
        to: "${env.CHANGE_AUTHOR_EMAIL}"
      )
    }
  }
}
```

### Scripted Pipeline

```groovy
node('docker') {
  try {
    stage('Checkout') {
      checkout scm
    }

    stage('Setup Services') {
      sh 'docker-compose -f docker-compose.test.yml up -d'
      sh 'sleep 10'
    }

    stage('API Tests') {
      dir('backend') {
        withEnv([
          'DATABASE_URL=postgresql://test:test@localhost:5432/test',
          'REDIS_URL=redis://localhost:6379/0'
        ]) {
          sh '''
            mvn clean test \
              -Dtest=karate.TestRunner \
              -Dbase.url=http://localhost:8000 \
              -Dkarate.threads=5
          '''
        }
      }
    }
  } finally {
    sh 'docker-compose -f docker-compose.test.yml down'
  }
}
```

## GitLab CI

```yaml
stages:
  - test
  - report

variables:
  MAVEN_OPTS: "-Dmaven.repo.local=.m2/repository"
  BASE_URL: "http://api:8000"

api_tests:
  stage: test
  image: maven:3.9-eclipse-temurin-11
  services:
    - postgres:14
    - redis:7
  variables:
    POSTGRES_USER: test
    POSTGRES_PASSWORD: test
    POSTGRES_DB: test
  cache:
    paths:
      - .m2/repository/
      - backend/.m2/repository/
  script:
    - cd backend
    - mvn clean test
        -Dtest=karate.TestRunner
        -Dbase.url=${BASE_URL}
        -Dkarate.threads=5
  artifacts:
    when: always
    reports:
      junit: backend/target/surefire-reports/**/*.xml
    paths:
      - backend/target/karate-reports/
    expire_in: 30 days
  only:
    - merge_requests
    - main
    - develop

publish_report:
  stage: report
  image: alpine:latest
  script:
    - echo "Test results available in artifacts"
  artifacts:
    paths:
      - backend/target/karate-reports/
  only:
    - merge_requests
```

## Azure Pipelines

```yaml
trigger:
  - main
  - develop

pr:
  - main
  - develop

pool:
  vmImage: 'ubuntu-latest'

variables:
  buildConfiguration: 'Release'
  javaVersion: '11'

stages:
  - stage: Test
    jobs:
      - job: KarateAPITests
        displayName: 'Run Karate API Tests'
        steps:
          - task: UseDotNet@2
            inputs:
              packageType: 'runtime'
              version: '6.0.x'

          - task: JavaToolInstaller@0
            inputs:
              versionSpec: $(javaVersion)
              addToPath: true

          - task: DockerCompose@0
            inputs:
              action: 'Run services'
              dockerComposeFile: 'docker-compose.test.yml'
              includeSourceTags: true

          - task: Maven@3
            inputs:
              mavenPomFile: 'backend/pom.xml'
              mavenOptions: '-Xmx3072m'
              javaHomeOption: 'JDKVersion'
              jdkVersionOption: $(javaVersion)
              goals: 'clean test'
              options: |
                -Dtest=karate.TestRunner
                -Dbase.url=http://localhost:8000
                -Dkarate.threads=5

          - task: PublishTestResults@2
            condition: succeededOrFailed()
            inputs:
              testResultsFormat: 'JUnit'
              testResultsFiles: '**/surefire-reports/*.xml'
              mergeTestResults: true
              testRunTitle: 'Karate API Test Results'

          - task: PublishBuildArtifacts@1
            condition: always()
            inputs:
              pathToPublish: 'backend/target/karate-reports'
              artifactName: 'karate-report'
```

## Docker Compose for Local CI Simulation

Create `docker-compose.test.yml`:

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:14-alpine
    environment:
      POSTGRES_USER: neurex
      POSTGRES_PASSWORD: neurex_test
      POSTGRES_DB: neurex_test
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U neurex"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  api:
    build:
      context: ./backend
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql://neurex:neurex_test@postgres:5432/neurex_test
      REDIS_URL: redis://redis:6379/0
      SECRET_KEY: test-secret
      JWT_SECRET: test-jwt-secret
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/health"]
      interval: 10s
      timeout: 5s
      retries: 5
```

Run locally:
```bash
docker-compose -f docker-compose.test.yml up --build
# In another terminal:
cd backend
mvn test -Dtest=karate.TestRunner -Dbase.url=http://localhost:8000
```

## Reporting and Notifications

### Slack Notifications

```groovy
def testStatus = currentBuild.result
def statusEmoji = testStatus == 'SUCCESS' ? '✅' : '❌'

slackSend(
  channel: '#qa-automation',
  message: """
    ${statusEmoji} Karate API Tests ${testStatus}
    Job: ${env.JOB_NAME}
    Build: ${env.BUILD_NUMBER}
    <${env.BUILD_URL}|View Details>
  """,
  color: testStatus == 'SUCCESS' ? 'good' : 'danger'
)
```

### Email Notifications

```groovy
emailext(
  to: 'qa-team@example.com',
  subject: "API Tests: ${currentBuild.fullDisplayName}",
  body: '''
    Test Results:
    ${TEST_COUNTS}
    
    See attached HTML report for details.
  ''',
  attachmentsPattern: 'backend/target/karate-reports/karate-summary.html'
)
```

### Custom HTML Report

The default Karate report includes:
- Test execution timeline
- Pass/fail breakdown by feature
- Response time metrics
- Detailed scenario logs

Reports available at:
```
backend/target/karate-reports/karate-summary.html
backend/target/karate-reports/karate-summary.txt
```

## Performance Baselines for CI

Adjust timeouts based on your CI environment:

| Environment | Threads | Avg Time | Timeout |
|-------------|---------|----------|---------|
| Local | 5 | 60s | 2m |
| GitHub Actions | 5 | 90s | 5m |
| Jenkins | 3 | 120s | 10m |
| Cloud (slow) | 2 | 180s | 15m |

## Troubleshooting CI Failures

### "Connection refused" to API
- Ensure backend has time to start (use healthchecks)
- Verify services are on same Docker network
- Add startup delay: `sleep 10` before tests

### Rate limit false positives
- CI environment may be slower, triggering rate limits
- Increase rate limit window or skip `@ratelimit` tests in CI:
  ```bash
  mvn test -Dkarate.options="--tags '@smoke or @critical'"
  ```

### Flaky tests on slow CI
- Increase timeouts in karate-config.js
- Add retries for async operations
- Use explicit waits instead of sleep

### OOM errors
- Reduce thread count: `-Dkarate.threads=2`
- Increase JVM memory: `-Xmx2g`

## Best Practices

1. **Run smoke tests on every PR** — quick feedback
2. **Run full suite on main branch** — comprehensive validation
3. **Keep test data consistent** — use seeded test users
4. **Monitor test execution time** — flag regressions early
5. **Archive reports** — maintain history for analysis
6. **Parallel execution** — balance speed vs resource usage
7. **Environment-specific configs** — dev/stage/prod URLs
