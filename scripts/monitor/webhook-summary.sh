#!/bin/bash

# Webhook Summary Report (Slack/Discord)
# No email configuration required!

# Configuration - Load Discord webhook URL from environment variable
# Add DISCORD_WEBHOOK_URL to your .env file
WEBHOOK_URL="${DISCORD_WEBHOOK_URL}"

if [ -z "$WEBHOOK_URL" ]; then
    echo "Error: DISCORD_WEBHOOK_URL environment variable not set"
    exit 1
fi

DATE=$(date '+%Y-%m-%d %H:%M')
HOSTNAME=$(hostname)

# Get metrics
TOTAL_FETCHED=$(journalctl -u reddit-fetcher.service --since "24 hours ago" | grep -o "fetched: [0-9]*" | awk -F': ' '{sum+=$2} END {print sum+0}')
TOTAL_PROCESSED=$(journalctl -u content-processor.service --since "24 hours ago" | grep -o "processed: [0-9]*" | awk -F': ' '{sum+=$2} END {print sum+0}')
ERROR_COUNT=$(journalctl -u reddit-fetcher.service -u content-processor.service --since "24 hours ago" -p err | wc -l)

# Get service status
FETCHER_STATUS=$(systemctl is-active reddit-fetcher.timer)
PROCESSOR_STATUS=$(systemctl is-active content-processor.timer)

# Create JSON payload properly
JSON_PAYLOAD=$(cat <<EOF
{
  "content": "📊 **AI Daily Digest Report** - $DATE\n\n**📈 24-Hour Summary:**\n• Reddit posts fetched: $TOTAL_FETCHED\n• Posts processed: $TOTAL_PROCESSED\n• Errors: $ERROR_COUNT\n\n**⚡ Services:** $FETCHER_STATUS | $PROCESSOR_STATUS\n**🖥️ Server:** $HOSTNAME"
}
EOF
)

# Send to Discord
curl -X POST "$WEBHOOK_URL" \
  -H "Content-Type: application/json" \
  -d "$JSON_PAYLOAD"

echo "Summary sent to webhook"