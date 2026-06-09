# Neurex Analytics + Slack Integration

## Overview

This document describes the complete Analytics and Slack integration implementation for Neurex. It includes event tracking, metrics aggregation, analytics dashboards, and real-time Slack notifications.

## Architecture

```
┌─────────────────┐
│  Application    │
│  Events         │
└────────┬────────┘
         │
    Creates
         │
         v
┌─────────────────────┐
│ AnalyticsEvent      │
│ - event_type        │
│ - event_name        │
│ - entity_id         │
│ - event_data (JSON) │
└────────┬────────────┘
         │
    Aggregates
         │
         v
┌──────────────────────┐
│ AnalyticsMetric      │
│ - metric_name        │
│ - metric_value       │
│ - date               │
│ - period             │
└────────┬─────────────┘
         │
    Consumed by
         │
    ┌────┴────────────┬──────────────┐
    │                 │              │
    v                 v              v
┌────────┐    ┌──────────────┐  ┌─────────────┐
│Dashboard│   │ Slack Events │  │ Exports     │
│ Charts  │   │ (Filtered)   │  │ (BigQuery)  │
└────────┘    └──────┬───────┘  └─────────────┘
                     │
                     v
              ┌──────────────────┐
              │SlackSubscription │
              │- webhook_url     │
              │- event_types     │
              └────────┬─────────┘
                       │
                       v
              ┌──────────────────────┐
              │SlackNotificationQueue│
              │- status: pending     │
              │- retry_count         │
              └────────┬─────────────┘
                       │
                       v
              ┌──────────────────┐
              │Slack API POST    │
              │(Incoming Webhook)│
              └─────────┬────────┘
                        │
                        v
              ┌──────────────────┐
              │SlackDeliveryLog  │
              │- success: bool   │
              │- timestamp       │
              └──────────────────┘
```

## Database Schema

### analytics_events
```sql
CREATE TABLE analytics_events (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    event_type VARCHAR(64) NOT NULL,           -- "test_run", "defect", "coverage"
    event_name VARCHAR(128) NOT NULL,          -- "test_run_started", "test_case_completed"
    entity_id UUID,
    entity_type VARCHAR(64),
    user_id UUID,
    project_id UUID,
    event_data JSONB DEFAULT '{}',
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_analytics_events_tenant ON analytics_events(tenant_id);
CREATE INDEX idx_analytics_events_type ON analytics_events(event_type);
CREATE INDEX idx_analytics_events_timestamp ON analytics_events(timestamp);
CREATE INDEX idx_analytics_events_tenant_type_ts ON analytics_events(tenant_id, event_type, timestamp);
```

### analytics_metrics
```sql
CREATE TABLE analytics_metrics (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    metric_name VARCHAR(128) NOT NULL,         -- "test_execution_count", "coverage_percentage"
    metric_category VARCHAR(64) NOT NULL,      -- "execution", "defect", "coverage"
    metric_value NUMERIC(15,2) NOT NULL,
    metric_unit VARCHAR(32),                   -- "count", "percentage", "hours"
    project_id UUID,
    team_id UUID,
    date DATE NOT NULL,
    period VARCHAR(32) NOT NULL,               -- "daily", "weekly", "monthly"
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_analytics_metrics_tenant ON analytics_metrics(tenant_id);
CREATE INDEX idx_analytics_metrics_name ON analytics_metrics(metric_name);
CREATE INDEX idx_analytics_metrics_date ON analytics_metrics(date);
CREATE INDEX idx_analytics_metrics_tenant_name_date ON analytics_metrics(tenant_id, metric_name, date);
```

### slack_subscriptions
```sql
CREATE TABLE slack_subscriptions (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    workspace_id VARCHAR(64) NOT NULL,
    channel_id VARCHAR(64) NOT NULL,
    channel_name VARCHAR(128),
    event_types JSONB NOT NULL DEFAULT '[]',
    webhook_url TEXT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_by UUID,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(tenant_id, workspace_id, channel_id)
);
```

### slack_notification_queue
```sql
CREATE TABLE slack_notification_queue (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    subscription_id UUID NOT NULL REFERENCES slack_subscriptions(id) ON DELETE CASCADE,
    event_id UUID NOT NULL REFERENCES analytics_events(id) ON DELETE CASCADE,
    webhook_url TEXT NOT NULL,
    message_body JSONB NOT NULL,
    status VARCHAR(32) DEFAULT 'pending',      -- pending, sent, failed, dlq
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    last_error TEXT,
    last_attempt_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Outbox pattern indexes
CREATE INDEX idx_slack_queue_status ON slack_notification_queue(status);
CREATE INDEX idx_slack_queue_status_tenant ON slack_notification_queue(status, tenant_id);
```

### slack_delivery_logs
```sql
CREATE TABLE slack_delivery_logs (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    notification_queue_id UUID REFERENCES slack_notification_queue(id) ON DELETE SET NULL,
    channel_id VARCHAR(64) NOT NULL,
    channel_name VARCHAR(128),
    message_ts VARCHAR(64),                    -- Slack message timestamp
    message_text TEXT,
    success BOOLEAN NOT NULL,
    status_code INTEGER,
    error_message TEXT,
    response_metadata JSONB DEFAULT '{}',
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Audit trail indexes
CREATE INDEX idx_slack_delivery_tenant ON slack_delivery_logs(tenant_id);
CREATE INDEX idx_slack_delivery_channel ON slack_delivery_logs(channel_id);
CREATE INDEX idx_slack_delivery_success ON slack_delivery_logs(success);
CREATE INDEX idx_slack_delivery_timestamp ON slack_delivery_logs(timestamp);
```

## API Endpoints

### Analytics Events

#### Create Event
```http
POST /api/v1/analytics/events
Content-Type: application/json
Authorization: Bearer <token>

{
  "event_type": "test_run",
  "event_name": "test_run_started",
  "entity_id": "test-run-123",
  "entity_type": "TestRun",
  "project_id": "project-1",
  "event_data": {
    "duration": 45.5,
    "test_count": 42,
    "environment": "staging"
  },
  "timestamp": "2026-06-09T15:30:00Z"
}
```

#### List Events
```http
GET /api/v1/analytics/events?event_type=test_run&limit=100
Authorization: Bearer <token>
```

### Analytics Metrics

#### Create Metric
```http
POST /api/v1/analytics/metrics
Content-Type: application/json
Authorization: Bearer <token>

{
  "metric_name": "test_execution_count",
  "metric_category": "execution",
  "metric_value": 42,
  "metric_unit": "count",
  "project_id": "project-1",
  "date": "2026-06-09",
  "period": "daily",
  "metadata": {
    "environment": "staging",
    "branch": "main"
  }
}
```

#### List Metrics
```http
GET /api/v1/analytics/metrics?metric_name=test_execution_count&start_date=2026-06-01&end_date=2026-06-09
Authorization: Bearer <token>
```

### Dashboard Endpoints

#### Get Dashboard Metrics
```http
GET /api/v1/analytics/dashboard/metrics?project_id=project-1
Authorization: Bearer <token>

Response:
{
  "test_execution_count": 42,
  "test_pass_rate": 95.5,
  "defect_rate": 0.8,
  "team_velocity": 42.0,
  "coverage_percentage": 85.2,
  "average_resolution_time": null,
  "flakiness_rate": 2.1,
  "data_period": "daily"
}
```

#### Get Trend Chart
```http
GET /api/v1/analytics/dashboard/trends?metric_name=test_execution_count&days=30
Authorization: Bearer <token>

Response:
{
  "title": "test_execution_count Trend",
  "metric_name": "test_execution_count",
  "unit": "count",
  "data_points": [
    {"date": "2026-05-10", "value": 35},
    {"date": "2026-05-11", "value": 38},
    ...
  ],
  "trend": "up",
  "change_percentage": 15.5
}
```

#### Get Coverage Heatmap
```http
GET /api/v1/analytics/dashboard/coverage-heatmap?project_id=project-1
Authorization: Bearer <token>

Response:
{
  "cells": [
    {
      "module": "auth",
      "test_type": "unit",
      "coverage_percentage": 92.5,
      "test_count": 45
    },
    ...
  ],
  "total_coverage": 85.2
}
```

### Slack Integration

#### Create Subscription
```http
POST /api/v1/analytics/slack/subscriptions
Content-Type: application/json
Authorization: Bearer <token>

{
  "workspace_id": "W123456",
  "channel_id": "C123456",
  "channel_name": "test-alerts",
  "event_types": ["test_run", "defect", "coverage"],
  "webhook_url": "https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX"
}
```

#### List Subscriptions
```http
GET /api/v1/analytics/slack/subscriptions?workspace_id=W123456
Authorization: Bearer <token>
```

#### Update Subscription
```http
PUT /api/v1/analytics/slack/subscriptions/{subscription_id}
Content-Type: application/json
Authorization: Bearer <token>

{
  "event_types": ["test_run", "defect"],
  "is_active": true
}
```

#### Delete Subscription
```http
DELETE /api/v1/analytics/slack/subscriptions/{subscription_id}
Authorization: Bearer <token>
```

#### Get Delivery Logs
```http
GET /api/v1/analytics/slack/delivery-logs?channel_id=C123456&success=true&limit=100
Authorization: Bearer <token>
```

#### Get Queue Status
```http
GET /api/v1/analytics/slack/queue-status
Authorization: Bearer <token>

Response:
{
  "total_pending": 5,
  "by_status": {
    "pending": 3,
    "failed": 2,
    "dlq": 0
  }
}
```

## Event Types

### Test Execution Events
- `test_run_started`: Test run initialization
- `test_run_completed`: Test run finished
- `test_case_completed`: Individual test case finished

### Defect Events
- `defect_created`: New defect reported
- `defect_resolved`: Defect marked as resolved

### Coverage Events
- `coverage_updated`: Code coverage metric updated

### Integration Events
- `team_velocity`: Team velocity metric calculated

## Metrics

### Execution Metrics
- `test_execution_count`: Number of tests executed
- `test_pass_rate`: Percentage of tests passed
- `flakiness_rate`: Percentage of flaky tests

### Defect Metrics
- `defect_created_count`: Number of defects created
- `defect_rate`: Defects per test execution
- `average_resolution_time`: Average time to resolve defects

### Coverage Metrics
- `coverage_percentage`: Code coverage percentage
- `coverage_change`: Change in coverage from previous period

### Team Metrics
- `team_velocity`: Tests executed per team member
- `execution_time`: Average test execution duration

## Slack Message Formatting

### Event Notification
```json
{
  "blocks": [
    {
      "type": "section",
      "text": {
        "type": "mrkdwn",
        "text": "*Test Run Completed*\nAll 42 tests passed in 45.5s"
      }
    },
    {
      "type": "section",
      "fields": [
        {
          "type": "mrkdwn",
          "text": "*Status*\nPassed"
        },
        {
          "type": "mrkdwn",
          "text": "*Duration*\n45.5s"
        }
      ]
    },
    {
      "type": "actions",
      "elements": [
        {
          "type": "button",
          "text": {"type": "plain_text", "text": "View Details"},
          "url": "https://app.neurex.io/runs/123"
        }
      ]
    }
  ]
}
```

### Daily Digest
```json
{
  "blocks": [
    {
      "type": "header",
      "text": {
        "type": "plain_text",
        "text": "Daily Summary - 2026-06-09"
      }
    },
    {
      "type": "section",
      "fields": [
        {
          "type": "mrkdwn",
          "text": "*Test Executions*\n42"
        },
        {
          "type": "mrkdwn",
          "text": "*Pass Rate*\n95.2%"
        },
        {
          "type": "mrkdwn",
          "text": "*Defects Created*\n3"
        },
        {
          "type": "mrkdwn",
          "text": "*Defects Resolved*\n2"
        }
      ]
    }
  ]
}
```

## Implementation Roadmap

### Week 1-2: Database & Models
- [x] Create analytics event schema
- [x] Create analytics metric schema
- [x] Create Slack subscription models
- [x] Create notification queue models
- [x] Database migrations

### Week 2-3: Analytics Service
- [x] Event creation and filtering
- [x] Metric aggregation logic
- [x] Dashboard metrics calculation
- [x] Trend analysis
- [x] Coverage heatmap

### Week 3-4: Slack Integration
- [x] Subscription management
- [x] Notification queue (outbox pattern)
- [x] Message formatting
- [x] Delivery logging
- [x] Retry logic (exponential backoff)

### Week 4-5: APIs and Workers
- [x] Analytics endpoints
- [x] Slack management endpoints
- [x] Background worker for retries
- [x] Daily digest scheduler

### Week 5-6: Testing
- [x] Unit tests for analytics service (20+ tests)
- [x] Unit tests for Slack service (15+ tests)
- [x] Integration tests for workflows
- [x] E2E tests for dashboard

### Week 6-7: Monitoring
- [ ] Metrics export to Prometheus
- [ ] Slack worker health checks
- [ ] Alert thresholds
- [ ] SLA monitoring

### Week 7-8: Production
- [ ] Load testing
- [ ] Batch processing for large datasets
- [ ] Backup & recovery procedures
- [ ] Documentation

## Configuration

### Environment Variables
```bash
# Analytics
ANALYTICS_BATCH_SIZE=1000
ANALYTICS_RETENTION_DAYS=365

# Slack
SLACK_WORKER_INTERVAL=300           # Process notifications every 5 minutes
SLACK_MAX_RETRIES=3
SLACK_RETRY_BACKOFF=1,2,5          # Exponential backoff in seconds
SLACK_API_TIMEOUT=10               # HTTP timeout in seconds
SLACK_DLQ_RETENTION_DAYS=30        # Dead letter queue retention

# Data Warehouse
BIGQUERY_PROJECT_ID=your-project
BIGQUERY_DATASET=neurex_analytics
CLICKHOUSE_HOST=localhost
CLICKHOUSE_PORT=8123
```

## Performance Considerations

### Indexing Strategy
- Composite indexes on (tenant_id, event_type, timestamp) for event queries
- Composite indexes on (tenant_id, metric_name, date) for metric queries
- Separate indexes on frequently filtered columns (status, success)

### Partitioning
- Partition analytics_events by tenant_id for multi-tenant isolation
- Partition by date for time-series operations

### Batch Processing
- Aggregate metrics in batches (e.g., 1000 events at a time)
- Use connection pooling for database connections
- Implement rate limiting for Slack API calls

### Data Retention
- Archive old events after 1 year
- Keep metrics indefinitely (monthly aggregates)
- Delete delivery logs after 90 days
- Configurable retention policies per tenant

## Security Considerations

### Data Privacy
- Encrypt webhook URLs in database
- Use secret management for Slack tokens
- Audit all Slack interactions
- PII filtering in event_data

### Access Control
- Permission checks (analytics.read, analytics.write, slack.manage)
- Tenant isolation at database level
- Rate limiting on API endpoints

### Webhook Validation
- Verify webhook signatures
- Validate webhook URLs (SSL, allowed hosts)
- Log all webhook deliveries

## Testing

Run the test suite:
```bash
cd backend

# Unit tests
pytest tests/unit/test_analytics_service.py -v
pytest tests/unit/test_slack_service.py -v

# Integration tests
pytest tests/integration/test_analytics_integration.py -v

# All tests
pytest tests/ -k "analytics or slack" -v
```

## Monitoring and Alerts

### Key Metrics to Monitor
- Event ingestion rate (events/minute)
- Metric aggregation latency (ms)
- Slack delivery success rate (%)
- Queue depth (pending notifications)
- Retry count (failed vs retried)

### Health Checks
- `/api/v1/health`: Overall service health
- `/api/v1/analytics/slack/queue-status`: Slack worker status
- Database connection pool status
- Kafka consumer lag (if using Kafka)

## Future Enhancements

- [ ] Real-time streaming via WebSockets
- [ ] Custom dashboards and widgets
- [ ] Predictive analytics (trends, anomalies)
- [ ] Integration with Datadog/New Relic
- [ ] Custom alert thresholds
- [ ] PDF report generation
- [ ] Mobile app analytics
- [ ] Team-specific views and permissions
