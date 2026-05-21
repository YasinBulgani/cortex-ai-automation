# =====================================================
#  Cortex Otomasyon Dashboard - Docker image
#  Tek bir konteynerda Java framework + Python dashboard.
# =====================================================
# Build: docker build -t cortex-otomasyon .
# Run:   docker run -p 5001:5001 -v $(pwd)/logs:/app/logs cortex-otomasyon
# =====================================================

FROM maven:3.9-eclipse-temurin-17 AS java-build
WORKDIR /build
COPY pom.xml ./
RUN mvn -B -q -DskipTests dependency:go-offline
COPY src ./src
RUN mvn -B -q -DskipTests package || true

# ---- runtime ----
FROM eclipse-temurin:17-jre-jammy

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DASHBOARD_PORT=5001 \
    DASHBOARD_HOST=0.0.0.0

# OS deps + Python + Chrome
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3 python3-pip python3-venv \
        maven \
        wget gnupg ca-certificates \
        fonts-liberation libnss3 libxss1 libasound2 libgbm1 \
    && rm -rf /var/lib/apt/lists/*

# Chrome (test koshumu icin)
RUN wget -q -O /tmp/chrome.deb \
        https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb \
    && apt-get update && apt-get install -y --no-install-recommends /tmp/chrome.deb \
    && rm /tmp/chrome.deb \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Java framework
COPY pom.xml ./
COPY src ./src
COPY --from=java-build /root/.m2 /root/.m2

# Python dashboard
COPY python_server ./python_server
COPY dashboard ./dashboard
COPY scripts ./scripts

RUN pip3 install --no-cache-dir -r python_server/requirements.txt

EXPOSE 5001
CMD ["python3", "python_server/flask_api.py"]
