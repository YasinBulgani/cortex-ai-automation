FROM python:3.14-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && playwright install --with-deps chromium

COPY . .

# Güvenlik: root olmayan kullanıcıyla çalıştır
# Playwright --with-deps root gerektirir (yukarıda tamamlandı),
# uygulama artık güvenli kullanıcıyla çalışır.
RUN groupadd -r appuser && useradd -r -g appuser -d /app -s /sbin/nologin appuser \
    && chown -R appuser:appuser /app \
    # Playwright tarayıcıları appuser tarafından da okunabilir olsun
    && chmod -R o+rX /root/.cache/ms-playwright 2>/dev/null || true

USER appuser

EXPOSE 5001

CMD ["python", "app.py"]
