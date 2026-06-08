FROM python:3.14-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Playwright tarayıcılarını sabit, appuser'a erişilebilir bir yola kur.
# Aksi halde build (root, HOME=/root) ile runtime (appuser, HOME=/app) farklı
# .cache yollarına bakar ve "headless_shell executable doesn't exist" hatası alınır.
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && playwright install --with-deps chromium \
    # appuser dahil herkes okuyabilsin/traverse edebilsin
    && chmod -R o+rX /ms-playwright

COPY . .

# Güvenlik: root olmayan kullanıcıyla çalıştır
# Playwright --with-deps root gerektirir (yukarıda tamamlandı),
# uygulama artık güvenli kullanıcıyla çalışır.
RUN groupadd -r appuser && useradd -r -g appuser -d /app -s /sbin/nologin appuser \
    && chown -R appuser:appuser /app

USER appuser

EXPOSE 5001

CMD ["python", "app.py"]
