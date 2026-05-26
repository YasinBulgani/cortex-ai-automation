# Jenkins Kurulum Rehberi

## Gerekli Credentials (P0 #2)

Jenkins'te aşağıdaki 5 credential tanımlanmalıdır:

| Credential ID | Tip | Açıklama |
|---|---|---|
| `ghcr-creds` | Username/Password | GitHub Container Registry — `ghcr.io` push için |
| `staging-db-url` | Secret Text | Staging PostgreSQL bağlantı URL'i |
| `staging-redis-url` | Secret Text | Staging Redis URL |
| `prod-db-url` | Secret Text | Production PostgreSQL — salt okunur CI pipeline için |
| `prod-deploy-key` | SSH Key | Production deploy sunucusu SSH anahtarı |

## Kurulum Adımları

### 1. GitHub Container Registry (`ghcr-creds`)

1. GitHub → Settings → Developer Settings → Personal access tokens → Fine-grained
2. Permissions: `packages:write`, `contents:read`
3. Jenkins → Manage Jenkins → Credentials → Add → Username/Password
   - ID: `ghcr-creds`
   - Username: GitHub kullanıcı adı
   - Password: token değeri

### 2. Staging Database (`staging-db-url`)

1. Jenkins → Manage Jenkins → Credentials → Add → Secret Text
   - ID: `staging-db-url`
   - Secret: `postgresql://user:pass@staging-host:5432/cortex_automation`

### 3. Staging Redis (`staging-redis-url`)

1. Jenkins → Manage Jenkins → Credentials → Add → Secret Text
   - ID: `staging-redis-url`
   - Secret: `redis://staging-host:6379/0`

### 4. Production Database (`prod-db-url`)

1. Jenkins → Manage Jenkins → Credentials → Add → Secret Text
   - ID: `prod-db-url`
   - Secret: `postgresql://readonly_user:pass@prod-host:5432/cortex_automation`
   - Not: Bu credential salt okunur bir kullanıcıyla yapılandırılmalıdır.

### 5. Production Deploy Key (`prod-deploy-key`)

1. Deploy sunucusunda SSH anahtar çifti oluştur: `ssh-keygen -t ed25519 -C "jenkins-deploy"`
2. Public key'i sunucunun `~/.ssh/authorized_keys` dosyasına ekle
3. Jenkins → Manage Jenkins → Credentials → Add → SSH Username with private key
   - ID: `prod-deploy-key`
   - Private key: yukarıda oluşturulan private key

## Pipeline Kullanımı

```groovy
pipeline {
    environment {
        REGISTRY_CREDS = credentials('ghcr-creds')
        STAGING_DB     = credentials('staging-db-url')
        STAGING_REDIS  = credentials('staging-redis-url')
    }
    stages {
        stage('Build & Push') {
            steps {
                sh '''
                  echo "$REGISTRY_CREDS_PSW" | docker login ghcr.io -u "$REGISTRY_CREDS_USR" --password-stdin
                  docker build -t ghcr.io/org/cortex-ai-automation:$BUILD_NUMBER .
                  docker push ghcr.io/org/cortex-ai-automation:$BUILD_NUMBER
                '''
            }
        }
        stage('Deploy Staging') {
            steps {
                sh 'DATABASE_URL=$STAGING_DB REDIS_URL=$STAGING_REDIS make deploy-staging'
            }
        }
        stage('Deploy Production') {
            when { branch 'main' }
            steps {
                sshagent(['prod-deploy-key']) {
                    sh 'ssh deploy@prod-host "make deploy-prod IMAGE=ghcr.io/org/cortex-ai-automation:$BUILD_NUMBER"'
                }
            }
        }
    }
}
```

## Doğrulama

`make ci-check` komutu ile tüm credentials'ların varlığı doğrulanabilir:

```bash
make ci-check
# Çıktı: ✓ ghcr-creds, ✓ staging-db-url, ✓ staging-redis-url, ✓ prod-db-url, ✓ prod-deploy-key
```

Herhangi bir credential eksikse Jenkins pipeline başlamadan önce hata verir.

## Güvenlik Notları

- Tüm credentials Jenkins Credentials Store'da şifreli tutulur.
- `prod-db-url` salt okunur bir DB kullanıcısına bağlı olmalıdır.
- Credentials ID'leri Jenkinsfile ile eşleşmelidir; değiştirilirse pipeline güncellenmeli.
- Her 90 günde bir token ve SSH anahtar rotasyonu önerilir.
