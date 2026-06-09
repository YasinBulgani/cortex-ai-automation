# Analytics + Slack Integration — Quick Start Guide

## 1. Database Setup

Run the migration:

```bash
cd backend
alembic upgrade head
```

This creates:
- `analytics_events` — raw event tracking
- `analytics_metrics` — aggregated metrics
- `slack_subscriptions` — Slack workspace integrations
- `slack_notification_queue` — retry queue (outbox pattern)
- `slack_delivery_logs` — audit trail
- `slack_daily_digests` — scheduled summaries

## 2. Create a Slack Subscription

### Get Your Slack Webhook URL

1. Go to your Slack workspace: https://api.slack.com/apps
2. Create a new app (or select existing)
3. Enable "Incoming Webhooks"
4. Create new webhook for a channel
5. Copy the webhook URL

### Subscribe to Events

```bash
curl -X POST http://localhost:8000/api/v1/analytics/slack/subscriptions \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "workspace_id": "W123456789",
    "channel_id": "C123456789",
    "channel_name": "#test-alerts",
    "event_types": ["test_run", "defect", "coverage"],
    "webhook_url": "https://hooks.slack.com/services/T00000000/B00000000/XXXX"
  }'
```

Response:
```json
{
  "id": "sub-123",
  "workspace_id": "W123456789",
  "channel_id": "C123456789",
  "event_types": ["test_run", "defect", "coverage"],
  "is_active": true,
  "created_at": "2026-06-09T15:30:00Z"
}
```

## 3. Track Analytics Events

### Track Test Run

```python
from app.domains.analytics.service import AnalyticsService
from app.domains.analytics import schemas as analytics_schemas

service = AnalyticsService(db)

event = analytics_schemas.AnalyticsEventCreate(
    event_type="test_run",
    event_name="test_run_started",
    entity_id="run-123",
    entity_type="TestRun",
    project_id="proj-1",
    event_data={
        "test_count": 42,
        "environment": "staging",
        "branch": "main",
    }
)

service.create_event("tenant-id", event)
```

### Track Defect

```python
event = analytics_schemas.AnalyticsEventCreate(
    event_type="defect",
    event_name="defect_created",
    entity_id="def-456",
    entity_type="Defect",
    project_id="proj-1",
    event_data={
        "title": "Login timeout",
        "severity": "high",
        "module": "auth",
    }
)

service.create_event("tenant-id", event)
```

### Track Coverage

```python
event = analytics_schemas.AnalyticsEventCreate(
    event_type="coverage",
    event_name="coverage_updated",
    project_id="proj-1",
    event_data={
        "coverage_percentage": 85.2,
        "previous_coverage": 84.1,
        "modules": {
            "auth": 92.5,
            "api": 81.0,
            "db": 79.5,
        }
    }
)

service.create_event("tenant-id", event)
```

## 4. Create Metrics

### Manual Metric Creation

```python
from datetime import date

metric = analytics_schemas.AnalyticsMetricCreate(
    metric_name="test_execution_count",
    metric_category="execution",
    metric_value=42,
    metric_unit="count",
    project_id="proj-1",
    date=date.today(),
    period="daily",
    metadata={
        "environment": "staging",
        "branch": "main",
    }
)

service.create_metric("tenant-id", metric)
```

### Automatic Aggregation

```python
# Aggregate events into metrics
service.aggregate_daily_metrics("tenant-id", date.today())
```

This automatically creates metrics like:
- `test_execution_count` — total tests run
- `defect_created_count` — total defects
- `test_pass_rate` — pass percentage
- `coverage_percentage` — code coverage

## 5. Query Analytics

### Get Events

```bash
curl http://localhost:8000/api/v1/analytics/events?event_type=test_run \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Get Metrics

```bash
curl http://localhost:8000/api/v1/analytics/metrics?metric_name=test_execution_count&start_date=2026-06-01 \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Get Dashboard Data

```bash
curl http://localhost:8000/api/v1/analytics/dashboard/metrics \
  -H "Authorization: Bearer YOUR_TOKEN"
```

Response:
```json
{
  "test_execution_count": 42,
  "test_pass_rate": 95.5,
  "defect_rate": 0.8,
  "team_velocity": 42.0,
  "coverage_percentage": 85.2,
  "flakiness_rate": 2.1,
  "data_period": "daily"
}
```

### Get Trends

```bash
curl 'http://localhost:8000/api/v1/analytics/dashboard/trends?metric_name=test_execution_count&days=30' \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## 6. Start the Slack Worker

### Background Worker

```python
import asyncio
from app.domains.analytics.slack_worker import start_worker

# Run in background (e.g., in a separate thread or process)
asyncio.run(start_worker(interval_seconds=300))
```

This:
- Processes pending notifications every 5 minutes
- Retries failed notifications (3 attempts max)
- Logs all deliveries to `slack_delivery_logs`
- Moves failed items to Dead Letter Queue (DLQ)

### Health Check

```bash
curl http://localhost:8000/api/v1/analytics/slack/queue-status \
  -H "Authorization: Bearer YOUR_TOKEN"
```

Response:
```json
{
  "total_pending": 5,
  "by_status": {
    "pending": 3,
    "failed": 2,
    "dlq": 0
  }
}
```

## 7. Slack Event Flow Example

When a test run completes:

1. **Event Created**
   ```python
   event = analytics_schemas.AnalyticsEventCreate(
       event_type="test_run",
       event_name="test_run_completed",
       event_data={"status": "passed", "duration": 45.5}
   )
   service.create_event("tenant-1", event)
   ```

2. **Subscription Matched**
   - System finds all active subscriptions for "test_run" events
   - Filters by tenant and active status

3. **Notification Queued**
   - Message created in `slack_notification_queue`
   - Status: "pending"

4. **Worker Processes**
   - Slack worker picks up pending notification
   - Makes HTTP POST to webhook URL
   - Logs result to `slack_delivery_logs`

5. **Slack Message Delivered**
   - Message appears in Slack channel
   - Rich formatting with test details, duration, pass rate

6. **Audit Trail**
   - All deliveries logged with timestamp, success/error
   - Metrics on delivery rate and latency

## 8. Daily Digest Configuration

### Schedule Digest

```bash
curl -X POST http://localhost:8000/api/v1/analytics/slack/digests/schedule \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "subscription_id": "sub-123",
    "schedule": "0 0 * * *",  # Every day at 00:00 UTC
    "include_metrics": ["test_execution_count", "defect_rate", "coverage_percentage"]
  }'
```

### Digest Content

```json
{
  "date": "2026-06-09",
  "test_executions": 42,
  "test_pass_rate": 95.5,
  "defects_created": 3,
  "defects_resolved": 2,
  "coverage_change": 1.5,
  "top_issues": [
    {"title": "Login timeout", "count": 3},
    {"title": "Memory leak", "count": 2}
  ]
}
```

## 9. Integration with Test Framework

### During Test Execution

```python
from app.domains.analytics.service import AnalyticsService
from app.domains.analytics import schemas as analytics_schemas

class TestRunner:
    def __init__(self, db, project_id):
        self.db = db
        self.project_id = project_id
        self.analytics = AnalyticsService(db)
    
    def run(self):
        # Start event
        self.analytics.create_event(
            "tenant-1",
            analytics_schemas.AnalyticsEventCreate(
                event_type="test_run",
                event_name="test_run_started",
                project_id=self.project_id,
                event_data={"test_count": 42}
            )
        )
        
        try:
            # Run tests
            results = self._execute_tests()
            
            # Complete event
            self.analytics.create_event(
                "tenant-1",
                analytics_schemas.AnalyticsEventCreate(
                    event_type="test_run",
                    event_name="test_run_completed",
                    project_id=self.project_id,
                    event_data={
                        "passed": results.passed,
                        "failed": results.failed,
                        "duration": results.duration,
                        "pass_rate": results.pass_rate,
                    }
                )
            )
        except Exception as e:
            # Error event
            self.analytics.create_event(
                "tenant-1",
                analytics_schemas.AnalyticsEventCreate(
                    event_type="test_run",
                    event_name="test_run_failed",
                    project_id=self.project_id,
                    event_data={"error": str(e)}
                )
            )
```

## 10. Troubleshooting

### No Messages in Slack?

1. Check webhook URL validity:
   ```bash
   curl -X POST https://hooks.slack.com/services/... \
     -H "Content-Type: application/json" \
     -d '{"text":"Test"}'
   ```

2. Check queue status:
   ```bash
   curl http://localhost:8000/api/v1/analytics/slack/queue-status
   ```

3. Review delivery logs:
   ```bash
   curl http://localhost:8000/api/v1/analytics/slack/delivery-logs?success=false
   ```

### Worker Not Running?

1. Verify worker is started in background
2. Check logs for errors
3. Verify database connection
4. Check rate limiting settings

### Missing Metrics?

1. Ensure events are created before aggregation
2. Run aggregation manually:
   ```python
   service.aggregate_daily_metrics("tenant-1", date.today())
   ```
3. Verify metric names are consistent
4. Check date/time zone handling

## 11. Performance Tips

### Bulk Event Creation
```python
events = [
    analytics_schemas.AnalyticsEventCreate(...),
    analytics_schemas.AnalyticsEventCreate(...),
    ...
]
for event in events:
    service.create_event("tenant-1", event)
# Commit once after batch
db.commit()
```

### Query Optimization
```python
# Use filters to reduce result set
events = service.get_events(
    tenant_id="tenant-1",
    event_type="test_run",
    project_id="proj-1",
    start_date=datetime.now() - timedelta(days=7),
    limit=100
)
```

### Batch Metric Aggregation
```python
from datetime import timedelta

# Aggregate last 7 days
for i in range(7):
    target_date = date.today() - timedelta(days=i)
    service.aggregate_daily_metrics("tenant-1", target_date)
```

## 12. Next Steps

- [ ] Set up automated event creation from test framework
- [ ] Configure daily digest schedules
- [ ] Create custom dashboard widgets
- [ ] Set up alerts on key metrics
- [ ] Export metrics to data warehouse
- [ ] Integrate with reporting tools
- [ ] Monitor worker health and performance
