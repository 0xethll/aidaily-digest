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

# Create message
MESSAGE="📊 **AI Daily Digest Report** - $DATE

**📈 24-Hour Summary:**
• Reddit posts fetched: $TOTAL_FETCHED
• Posts processed: $TOTAL_PROCESSED  
• Errors: $ERROR_COUNT

**⚡ Services:** $(systemctl is-active reddit-fetcher.timer) | $(systemctl is-active content-processor.timer)
**🖥️ Server:** $HOSTNAME"

# Send to Discord
curl -X POST "$WEBHOOK_URL" \
  -H "Content-Type: application/json" \
  -d "{\"content\":\"$MESSAGE\"}"

echo "Summary sent to webhook"