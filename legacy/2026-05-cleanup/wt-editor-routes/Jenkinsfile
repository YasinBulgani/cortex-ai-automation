pipeline {
  agent any

  options {
    ansiColor('xterm')
    timestamps()
    disableConcurrentBuilds()
    buildDiscarder(logRotator(numToKeepStr: '20'))
    timeout(time: 120, unit: 'MINUTES')
  }

  parameters {
    choice(name: 'TEST_SUITE', choices: ['smoke', 'standard', 'full'], description: 'Calistirilacak Jenkins test kapsamı')
    booleanParam(name: 'PUSH_IMAGES', defaultValue: false, description: 'Docker image push yap')
    booleanParam(name: 'DEPLOY_STAGING', defaultValue: false, description: 'Staging deploy yap')
    booleanParam(name: 'DEPLOY_PRODUCTION', defaultValue: false, description: 'Production deploy yap')
    string(name: 'IMAGE_TAG', defaultValue: '', description: 'Opsiyonel image tag, bossa commit short sha kullanilir')
    string(name: 'REGISTRY_REPO', defaultValue: 'ghcr.io/bgts/bgts', description: 'Image repo prefix, ornek: ghcr.io/acme/bgts')
    string(name: 'NOTIFY_EMAIL_TO', defaultValue: '', description: 'Opsiyonel e-posta bildirim listesi')
  }

  environment {
    REPORTS_DIR = 'reports'
    IMAGE_TAG = "${params.IMAGE_TAG}"
  }

  stages {
    stage('Checkout') {
      steps {
        checkout scm
        sh 'mkdir -p reports'
        sh 'chmod +x scripts/ci/*.sh'
      }
    }

    stage('Verify Tooling') {
      steps {
        sh '''
          python3 --version
          node --version
          npm --version
          docker --version
        '''
      }
    }

    stage('Parallel Checks') {
      parallel {
        stage('Frontend Checks') {
          steps {
            sh './scripts/ci/test.sh frontend'
          }
        }

        stage('Backend Lint') {
          steps {
            sh './scripts/ci/test.sh lint'
          }
        }

        stage('Engine Unit') {
          steps {
            sh './scripts/ci/test.sh engine-unit'
          }
        }
      }
    }

    stage('Backend Smoke') {
      steps {
        sh './scripts/ci/test.sh backend-smoke'
      }
    }

    stage('Backend Service') {
      when {
        anyOf {
          expression { return params.TEST_SUITE == 'standard' }
          expression { return params.TEST_SUITE == 'full' }
        }
      }
      steps {
        sh './scripts/ci/test.sh backend-service'
      }
    }

    stage('Backend API') {
      when {
        anyOf {
          expression { return params.TEST_SUITE == 'standard' }
          expression { return params.TEST_SUITE == 'full' }
        }
      }
      steps {
        sh './scripts/ci/test.sh backend-api'
      }
    }

    stage('BDD API') {
      when {
        anyOf {
          expression { return params.TEST_SUITE == 'standard' }
          expression { return params.TEST_SUITE == 'full' }
        }
      }
      steps {
        sh './scripts/ci/test.sh bdd-api'
      }
    }

    stage('E2E Smoke') {
      steps {
        sh './scripts/ci/test.sh e2e-smoke'
      }
    }

    stage('E2E Regression') {
      when {
        expression { return params.TEST_SUITE == 'full' }
      }
      steps {
        sh './scripts/ci/test.sh e2e-regression'
      }
    }

    stage('Allure Report') {
      when {
        anyOf {
          expression { return params.TEST_SUITE == 'standard' }
          expression { return params.TEST_SUITE == 'full' }
        }
      }
      steps {
        catchError(buildResult: 'SUCCESS', stageResult: 'UNSTABLE') {
          sh './scripts/ci/allure.sh'
        }
        script {
          if (fileExists('reports/allure-report/index.html')) {
            try {
              publishHTML(target: [
                allowMissing: true,
                alwaysLinkToLastBuild: true,
                keepAll: true,
                reportDir: 'reports/allure-report',
                reportFiles: 'index.html',
                reportName: 'Allure Report'
              ])
            } catch (err) {
              echo "HTML Publisher plugin not available, Allure report will remain as archived artifact."
            }
          } else {
            echo 'No generated Allure HTML report found.'
          }
        }
      }
    }

    stage('Build Docker Images') {
      when {
        anyOf {
          branch 'main'
          expression { return params.PUSH_IMAGES }
        }
      }
      steps {
        sh '''
          EFFECTIVE_TAG="${IMAGE_TAG:-$(git rev-parse --short HEAD)}"

          docker build -t "${REGISTRY_REPO}-backend:${EFFECTIVE_TAG}" backend
          docker build -t "${REGISTRY_REPO}-engine:${EFFECTIVE_TAG}" engine
          docker build -t "${REGISTRY_REPO}-web:${EFFECTIVE_TAG}" apps/web
          docker build -t "${REGISTRY_REPO}-ai-gateway:${EFFECTIVE_TAG}" ai-gateway
        '''
      }
    }

    stage('Push Docker Images') {
      when {
        expression { return params.PUSH_IMAGES }
      }
      steps {
        withCredentials([usernamePassword(credentialsId: 'ghcr-creds', usernameVariable: 'REGISTRY_USER', passwordVariable: 'REGISTRY_TOKEN')]) {
          sh '''
            EFFECTIVE_TAG="${IMAGE_TAG:-$(git rev-parse --short HEAD)}"
            echo "$REGISTRY_TOKEN" | docker login ghcr.io -u "$REGISTRY_USER" --password-stdin

            docker push "${REGISTRY_REPO}-backend:${EFFECTIVE_TAG}"
            docker push "${REGISTRY_REPO}-engine:${EFFECTIVE_TAG}"
            docker push "${REGISTRY_REPO}-web:${EFFECTIVE_TAG}"
            docker push "${REGISTRY_REPO}-ai-gateway:${EFFECTIVE_TAG}"
          '''
        }
      }
    }

    stage('Deploy Staging') {
      when {
        expression { return params.DEPLOY_STAGING }
      }
      steps {
        sshagent(credentials: ['staging-ssh-key']) {
          withCredentials([
            string(credentialsId: 'staging-host', variable: 'DEPLOY_HOST'),
            string(credentialsId: 'staging-user', variable: 'DEPLOY_USER'),
            string(credentialsId: 'staging-path', variable: 'DEPLOY_PATH')
          ]) {
            sh '''
              export IMAGE_TAG="${IMAGE_TAG:-$(git rev-parse --short HEAD)}"
              ./scripts/ci/deploy.sh staging
            '''
          }
        }
      }
    }

    stage('Production Approval') {
      when {
        expression { return params.DEPLOY_PRODUCTION }
      }
      steps {
        input message: 'Production deploy baslatilsin mi?', ok: 'Deploy'
      }
    }

    stage('Deploy Production') {
      when {
        expression { return params.DEPLOY_PRODUCTION }
      }
      steps {
        sshagent(credentials: ['prod-ssh-key']) {
          withCredentials([
            string(credentialsId: 'prod-host', variable: 'DEPLOY_HOST'),
            string(credentialsId: 'prod-user', variable: 'DEPLOY_USER'),
            string(credentialsId: 'prod-path', variable: 'DEPLOY_PATH')
          ]) {
            sh '''
              export IMAGE_TAG="${IMAGE_TAG:-$(git rev-parse --short HEAD)}"
              ./scripts/ci/deploy.sh production
            '''
          }
        }
      }
    }
  }

  post {
    success {
      catchError(buildResult: 'SUCCESS', stageResult: 'FAILURE') {
        sh './scripts/ci/notify.sh bgts-ci SUCCESS "${BUILD_URL}"'
      }
      script {
        if (params.NOTIFY_EMAIL_TO?.trim()) {
          mail(
            to: params.NOTIFY_EMAIL_TO.trim(),
            subject: "BGTS CI SUCCESS: ${env.JOB_NAME} #${env.BUILD_NUMBER}",
            body: "Build basarili.\n\nJob: ${env.JOB_NAME}\nBuild: #${env.BUILD_NUMBER}\nSuite: ${params.TEST_SUITE}\nURL: ${env.BUILD_URL}"
          )
        }
      }
    }
    unstable {
      catchError(buildResult: 'UNSTABLE', stageResult: 'FAILURE') {
        sh './scripts/ci/notify.sh bgts-ci UNSTABLE "${BUILD_URL}"'
      }
      script {
        if (params.NOTIFY_EMAIL_TO?.trim()) {
          mail(
            to: params.NOTIFY_EMAIL_TO.trim(),
            subject: "BGTS CI UNSTABLE: ${env.JOB_NAME} #${env.BUILD_NUMBER}",
            body: "Build unstable durumunda tamamlandi.\n\nJob: ${env.JOB_NAME}\nBuild: #${env.BUILD_NUMBER}\nSuite: ${params.TEST_SUITE}\nURL: ${env.BUILD_URL}"
          )
        }
      }
    }
    failure {
      catchError(buildResult: 'FAILURE', stageResult: 'FAILURE') {
        sh './scripts/ci/notify.sh bgts-ci FAILURE "${BUILD_URL}"'
      }
      script {
        if (params.NOTIFY_EMAIL_TO?.trim()) {
          mail(
            to: params.NOTIFY_EMAIL_TO.trim(),
            subject: "BGTS CI FAILURE: ${env.JOB_NAME} #${env.BUILD_NUMBER}",
            body: "Build basarisiz oldu.\n\nJob: ${env.JOB_NAME}\nBuild: #${env.BUILD_NUMBER}\nSuite: ${params.TEST_SUITE}\nURL: ${env.BUILD_URL}"
          )
        }
      }
    }
    always {
      junit testResults: 'reports/*.xml', allowEmptyResults: true
      archiveArtifacts artifacts: 'reports/**/*', allowEmptyArchive: true
      deleteDir()
    }
  }
}
