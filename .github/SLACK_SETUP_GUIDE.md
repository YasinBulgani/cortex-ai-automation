# Slack Webhook Setup for GitHub Actions

## Prerequisites

- GitHub repository admin access
- Slack workspace admin access

## Step 1: Create Slack App

1. Go to https://api.slack.com/apps
2. Click **Create New App**
3. Select **From scratch**
4. App Name: `Cortex CI/CD`
5. Select workspace
6. Click **Create App**

## Step 2: Enable Incoming Webhooks

1. Left sidebar → **Incoming Webhooks**
2. Toggle **Activate Incoming Webhooks** to ON
3. Click **Add New Webhook to Workspace**
4. Select channel (e.g., `#ci-deployments`)
5. Click **Allow**
6. Copy Webhook URL (format: `https://hooks.slack.com/services/T.../B.../X...`)

## Step 3: Add to GitHub Secrets

1. Go to repository
2. **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Name: `SLACK_WEBHOOK_URL`
5. Value: Paste webhook URL
6. Click **Add secret**

## Step 4: Verify Setup

```bash
curl -X POST "WEBHOOK_URL" \
  -H 'Content-Type: application/json' \
  -d '{"text":"Test from GitHub Actions"}'
```

You should see the message in Slack.

## Troubleshooting

- **URL invalid**: Check format starts with `https://hooks.slack.com/services/`
- **Message not appearing**: Check app is invited to channel
- **Permission denied**: Verify workspace admin access

---

**Status**: Production Ready
