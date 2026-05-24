# Hafta 12 - Backend Integration Guide
## Complete Step-by-Step Integration Instructions

**Status**: 🚀 **INTEGRATION IN PROGRESS**
**Date**: 2026-04-05
**Phase**: Backend Connection & End-to-End Testing

---

## 🚀 Phase 1: Backend Startup (Immediate)

### Step 1: Start Flask API Server

**Terminal 1: Start Backend**
```bash
# Navigate to project root
cd /Users/yasin_bulgan/Cortex_Ai_Automation

# Activate Python virtual environment (if using venv)
source venv/bin/activate  # macOS/Linux
# or
venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Start Flask server
export FLASK_ENV=development
export FLASK_DEBUG=True
python -m services.flask_app
```

**Expected Output**:
```
 * Running on http://127.0.0.1:8000
 * Debug mode: on
```

---

### Step 2: Verify API Health Check

**Terminal 2: Test API Endpoint**
```bash
# Test health check
curl http://localhost:8000/api/health

# Expected response:
{
  "status": "healthy",
  "service": "BGTS-Test-Donusum",
  "version": "1.0.0",
  "timestamp": "2026-04-05T12:34:56.789012"
}
```

---

### Step 3: Start React Frontend

**Terminal 3: Start Frontend**
```bash
# Navigate to frontend directory
cd /Users/yasin_bulgan/Cortex_Ai_Automation/website/frontend

# Install dependencies
npm install

# Create .env file with backend URL
echo "REACT_APP_API_URL=http://localhost:8000" > .env
echo "REACT_APP_WS_URL=ws://localhost:8000/ws" >> .env

# Start development server
npm start
```

**Expected Output**:
```
Compiled successfully!
Local:            http://localhost:3000
```

---

## 🔌 Phase 2: Connection Verification

### Test 1: API Health Check from Frontend

**In Browser Console (F12)**:
```javascript
// Test API health
fetch('http://localhost:8000/api/health')
  .then(r => r.json())
  .then(data => console.log('✅ API Health:', data))
  .catch(e => console.error('❌ API Error:', e));
```

**Expected**:
```
✅ API Health: {
  status: 'healthy',
  service: 'BGTS-Test-Donusum',
  version: '1.0.0',
  timestamp: '2026-04-05T...'
}
```

---

### Test 2: WebSocket Connection

**In Browser Console**:
```javascript
// Test WebSocket connection
const ws = new WebSocket('ws://localhost:8000/ws');

ws.onopen = () => {
  console.log('✅ WebSocket Connected');
};

ws.onmessage = (event) => {
  console.log('📨 Message:', event.data);
};

ws.onerror = (error) => {
  console.error('❌ WebSocket Error:', error);
};

ws.onclose = () => {
  console.log('⚠️ WebSocket Closed');
};
```

---

### Test 3: API Client Integration

**In Browser Console**:
```javascript
// Test API client
const apiClient = window.apiClient || new window.APIClient({
  baseUrl: 'http://localhost:8000'
});

// Test health endpoint
apiClient.healthCheck()
  .then(data => console.log('✅ API Client Working:', data))
  .catch(e => console.error('❌ API Client Error:', e));
```

---

## 🧪 Phase 3: API Endpoint Testing

### Test Project Management Endpoints

**Test 1: List Projects**
```bash
curl -X GET http://localhost:8000/api/projects \
  -H "Content-Type: application/json"
```

**Expected Response**:
```json
{
  "projects": [
    {
      "id": "1",
      "name": "Sample Project",
      "environment": "development"
    }
  ]
}
```

**Test 2: Create Project**
```bash
curl -X POST http://localhost:8000/api/projects \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Integration Test Project",
    "description": "Test project for Hafta 12",
    "environment": "development"
  }'
```

---

### Test AI API Endpoints

**Test 1: Generate Scenarios**
```bash
curl -X POST http://localhost:8000/api/ai/generate-scenarios \
  -H "Content-Type: application/json" \
  -d '{
    "user_story": "As a user, I want to login to the platform",
    "page_url": "https://example.com/login",
    "page_elements": ["username", "password", "login-button"]
  }'
```

**Test 2: Suggest Test Data**
```bash
curl -X POST http://localhost:8000/api/ai/suggest-data \
  -H "Content-Type: application/json" \
  -d '{
    "scenario_description": "User login with valid credentials",
    "required_fields": ["username", "password"],
    "test_type": "happy_path"
  }'
```

---

### Test Reporting Endpoints

**Test 1: Record Test Run**
```bash
curl -X POST http://localhost:8000/api/reporting/record-run \
  -H "Content-Type: application/json" \
  -d '{
    "run_id": "test-run-001",
    "total_tests": 10,
    "passed_tests": 9,
    "failed_tests": 1,
    "duration": 45
  }'
```

**Test 2: Get Analytics**
```bash
curl -X GET "http://localhost:8000/api/reporting/analytics/trends?hours=24" \
  -H "Content-Type: application/json"
```

---

## 🔐 Environment Configuration

### Create Backend .env File

**File**: `/Users/yasin_bulgan/Cortex_Ai_Automation/.env`

```env
# Flask Configuration
FLASK_ENV=development
FLASK_DEBUG=True
SECRET_KEY=your-secret-key-here

# Database Configuration
DATABASE_URL=sqlite:///data/database.sqlite
# or for PostgreSQL:
# DATABASE_URL=postgresql://user:password@localhost/bgts_testdb

# AI Provider Keys
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
DEEPSEEK_API_KEY=sk-...
OLLAMA_URL=http://localhost:11434

# Server Configuration
HOST=0.0.0.0
PORT=8000
LOG_LEVEL=INFO

# Frontend Configuration
FRONTEND_URL=http://localhost:3000
CORS_ORIGINS=http://localhost:3000,http://localhost:8000

# Feature Flags
ENABLE_AI_GENERATION=true
ENABLE_VISUAL_REGRESSION=true
ENABLE_ACCESSIBILITY_TESTING=true
ENABLE_SYNTHETIC_DATA=true
```

---

## 📊 Integration Testing Checklist

### API Endpoint Tests
- [ ] GET `/api/health` - Returns 200 with health status
- [ ] GET `/api/status` - Returns service status
- [ ] GET `/api/version` - Returns version info
- [ ] GET `/api/projects` - Returns project list
- [ ] POST `/api/projects` - Creates new project
- [ ] GET `/api/projects/{id}` - Gets project details
- [ ] PUT `/api/projects/{id}` - Updates project
- [ ] DELETE `/api/projects/{id}` - Deletes project

### AI API Tests
- [ ] POST `/api/ai/generate-scenarios` - Generates test scenarios
- [ ] POST `/api/ai/suggest-data` - Suggests test data
- [ ] POST `/api/ai/analyze-coverage` - Analyzes coverage
- [ ] GET `/api/ai/statistics` - Gets AI statistics
- [ ] GET `/api/ai/config` - Gets configuration

### Reporting API Tests
- [ ] POST `/api/reporting/record-run` - Records test run
- [ ] POST `/api/reporting/generate-report` - Generates report
- [ ] GET `/api/reporting/analytics/trends` - Gets trends
- [ ] GET `/api/reporting/analytics/risk-assessment` - Risk assessment
- [ ] GET `/api/reporting/analytics/predictions` - Predictions

### WebSocket Tests
- [ ] Connection establishes successfully
- [ ] test_started events received
- [ ] test_passed events received
- [ ] test_failed events received
- [ ] step_started events received
- [ ] screenshot events received
- [ ] progress events received
- [ ] completed events received

### Frontend Integration Tests
- [ ] Dashboard loads correctly
- [ ] API data displays properly
- [ ] Real-time updates work
- [ ] Navigation functions
- [ ] Forms submit correctly
- [ ] Reports generate
- [ ] Analytics display
- [ ] Settings persist

---

## 🔍 Troubleshooting

### Issue: API Not Responding

**Symptoms**:
- `curl: (7) Failed to connect`
- Connection refused on port 8000

**Solutions**:
```bash
# Check if port is in use
lsof -i :8000

# Kill process using port
kill -9 <PID>

# Verify Flask is installed
pip list | grep Flask

# Reinstall dependencies
pip install -r requirements.txt

# Start Flask with explicit host/port
python -m services.flask_app --host=0.0.0.0 --port=8000
```

---

### Issue: CORS Errors

**Symptoms**:
- `Access to XMLHttpRequest blocked by CORS`
- Cross-Origin Request Blocked

**Solutions**:
```bash
# Check CORS configuration in flask_app.py
# Verify frontend URL is in CORS_ORIGINS

# Update .env
CORS_ORIGINS=http://localhost:3000

# Restart Flask server
```

---

### Issue: WebSocket Connection Failed

**Symptoms**:
- `WebSocket is closed before the connection is established`
- `Error during WebSocket handshake`

**Solutions**:
```bash
# Check Flask-SocketIO is installed
pip install flask-socketio python-socketio

# Verify WebSocket endpoint is registered
# Check /api/ws endpoint in flask_app.py

# Check browser console for connection errors
# Verify ws:// URL is correct (not http://)
```

---

### Issue: Database Connection Error

**Symptoms**:
- `No such file or directory: 'database.sqlite'`
- `Connection refused` (PostgreSQL)

**Solutions**:
```bash
# Create database directory
mkdir -p data

# Initialize database
python -c "from services.database import init_db; init_db()"

# For PostgreSQL, ensure it's running:
# macOS: brew services start postgresql
# Linux: sudo systemctl start postgresql
```

---

## 📈 Performance Verification

### Load Test Script

**File**: `test_load.py`
```python
import requests
import time
from concurrent.futures import ThreadPoolExecutor

BASE_URL = "http://localhost:8000"

def test_endpoint(endpoint):
    start = time.time()
    try:
        response = requests.get(f"{BASE_URL}{endpoint}")
        duration = time.time() - start
        return {
            'endpoint': endpoint,
            'status': response.status_code,
            'duration': duration,
            'success': response.status_code == 200
        }
    except Exception as e:
        return {
            'endpoint': endpoint,
            'error': str(e),
            'success': False
        }

# Test endpoints
endpoints = [
    '/api/health',
    '/api/status',
    '/api/projects',
    '/api/ai/statistics',
    '/api/reporting/analytics/trends'
]

print("🧪 Load Testing...")
with ThreadPoolExecutor(max_workers=5) as executor:
    results = list(executor.map(test_endpoint, endpoints * 10))

# Analyze results
success = sum(1 for r in results if r.get('success'))
avg_duration = sum(r.get('duration', 0) for r in results) / len(results)

print(f"✅ Success Rate: {success}/{len(results)} ({100*success/len(results):.1f}%)")
print(f"⏱️  Average Duration: {avg_duration*1000:.2f}ms")
```

**Run Test**:
```bash
python test_load.py
```

---

## 🎉 Integration Success Criteria

- ✅ Backend API responding on localhost:8000
- ✅ Frontend dashboard accessible on localhost:3000
- ✅ All API endpoints working correctly
- ✅ WebSocket connection established
- ✅ Real-time events streaming
- ✅ Database operations functional
- ✅ CORS properly configured
- ✅ Error handling working
- ✅ Performance within benchmarks
- ✅ No console errors

---

## 📋 Next Steps

Once all tests pass:
1. Run full end-to-end test suite
2. Performance optimization
3. Security hardening
4. Docker containerization
5. Kubernetes deployment

---

**Guide Created**: 2026-04-05
**Status**: 🚀 **READY FOR BACKEND INTEGRATION**
