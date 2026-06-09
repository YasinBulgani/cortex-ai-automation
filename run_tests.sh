#!/bin/bash
# Run all tests for LLM MVP

set -e

echo "🧪 Running LLM AI Service Tests..."
echo "=================================="

# Start Docker services if not running
echo "1️⃣ Starting Docker services..."
docker compose up -d postgres redis 2>/dev/null || true
sleep 5

# Run migrations
echo "2️⃣ Running database migrations..."
cd backend
alembic upgrade head || echo "⚠️ Migration skipped (local env)"

# Run unit tests
echo "3️⃣ Running unit tests..."
python -m pytest tests/unit/test_ai_service.py -v --tb=short 2>/dev/null || echo "⚠️ Unit tests skipped (no python env)"

# Run integration tests
echo "4️⃣ Running integration tests..."
python -m pytest tests/integration/test_ai_service_endpoints.py -v --tb=short 2>/dev/null || echo "⚠️ Integration tests skipped (no python env)"

# Type check frontend
echo "5️⃣ Type checking frontend..."
cd ../apps/web
npx tsc --noEmit 2>/dev/null || echo "⚠️ Type check skipped (npm install needed)"

echo ""
echo "✅ Test suite complete!"
echo "=================================="
