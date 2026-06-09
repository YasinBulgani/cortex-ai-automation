# Slack Webhook Setup for CI/CD Pipeline

This guide explains how to configure GitHub Actions to send test pipeline notifications to Slack.

## Prerequisites

- GitHub repository admin access
- Slack workspace admin access
- Slack bot creation permission

## Step-by-Step Setup

### 1. Create a Slack App

1. Go to [api.slack.com](https://api.slack.com/apps)
2. Click **Create New App**
3. Select **From scratch**
4. **App Name**: `Cortex CI/CD` (or your preferred name)
5. **Pick a workspace**: Select your Slack workspace
6. Click **Create App**

### 2. Enable Incoming Webhooks

1. In the left sidebar, click **Incoming Webhooks**
2. Toggle **Activate Incoming Webhooks** to **ON**
3. Click **Add New Webhook to Workspace**
4. **Select a channel**: Choose the channel where you want notifications (e.g., `#ci-deployments`)
5. Click **Allow**
6. **Copy the Webhook URL** - it will look like:
   ```
   https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXX
   ```

### 3. Add to GitHub Secrets

1. Go to your GitHub repository
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. **Name**: `SLACK_WEBHOOK_URL`
5. **Value**: Paste the Webhook URL from step 2
6. Click **Add secret**

### 4. Verify the Setup

Test the webhook manually:

```bash
# Replace with your actual URL
WEBHOOK_URL="https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXX"

curl -X POST "$WEBHOOK_URL" \
  -H 'Content-Type: application/json' \
  -d '{
    "text": "Test notification from GitHub Actions",
    "blocks": [
      {
        "type": "section",
        "text": {
          "type": "mrkdwn",
          "text": "*Test Message* ✅\nThis is a test from GitHub Actions"
        }
      }
    ]
  }'
```

If successful, you should see the message in your Slack channel.

## Notification Types

### Success Notification
```
Test Pipeline Passed ✅
Branch: main
Commit: a1b2c3d...
```

### Failure Notification
```
Test Pipeline Failed 🔴
Branch: feature/qa-system-bootstrap
Commit: x9y8z7w...
Author: @developer

Unit Tests: failure
API Tests: success
Frontend Tests: success
E2E Tests: failure

[View Run]
```

## Advanced Configuration

### Customize the Channel

If you want different workflows to notify different channels, you can create multiple webhooks:

1. Create a new webhook for another channel
2. Add another GitHub secret (e.g., `SLACK_WEBHOOK_URL_QA`)
3. Reference it in the workflow YAML

### Mention Users on Failure

To mention users when tests fail, modify the Slack block in `.github/workflows/test-automation.yml`:

```yaml
"text": "*Test Pipeline Failed* 🔴\nCC: <@userid> <@another-userid>\n*Branch:* `${{ github.ref_name }}`"
```

To find user IDs:
1. Right-click user's profile in Slack
2. Copy member ID (starts with `U...`)

### Custom Color for Status

Use the `color` field in Slack blocks:

```yaml
{
  "type": "section",
  "text": {...},
  "accessory": {
    "type": "button",
    "style": "danger"  # Red background for failures
  }
}
```

## Troubleshooting

### Webhook URL Invalid
- Double-check the URL is copied completely
- Verify it starts with `https://hooks.slack.com/services/`
- Check for trailing spaces

### Message Not Appearing
1. Verify the Slack app is invited to the channel:
   ```
   /invite @Cortex-CI-CD
   ```
2. Check the GitHub secret name matches `SLACK_WEBHOOK_URL`
3. View GitHub Actions workflow logs for errors

### Multiple Failed Notifications
This might indicate:
- The webhook is working (good!)
- But multiple workflows are triggering
- Configure workflow triggers in `.github/workflows/test-automation.yml`

## Security Best Practices

1. **Never commit webhook URLs** - Always use GitHub Secrets
2. **Rotate webhooks periodically** - Regenerate and update the secret
3. **Use dedicated app** - Don't mix with other integrations
4. **Limit channel access** - Keep the notification channel private if needed
5. **Review app permissions** - Remove unnecessary scopes

## Revoking Access

If you need to revoke the webhook:

1. Go to [api.slack.com](https://api.slack.com/apps)
2. Select **Cortex CI/CD**
3. Click **Incoming Webhooks**
4. Find the webhook and click **Delete**
5. Update GitHub secret if needed

## GitHub Actions Secret Verification

```bash
# List all secrets (doesn't show values)
gh secret list --repo <owner>/<repo>

# Verify the secret exists
gh secret view SLACK_WEBHOOK_URL --repo <owner>/<repo>
```

## References

- [Slack Incoming Webhooks Documentation](https://api.slack.com/messaging/webhooks)
- [GitHub Actions Secrets Documentation](https://docs.github.com/en/actions/security-guides/encrypted-secrets)
- [Slack Block Kit Documentation](https://api.slack.com/block-kit)

---

**Last Updated**: 2026-06-09
**Maintained By**: Cortex AI Team
