#!/bin/bash

# Daily Summary Report Generator
# Sends email with Reddit fetch and processing statistics

# Configuration
TO_EMAIL="hlxstc680@gmail.com"
REPORT_PERIOD="24 hours ago"  # or "12 hours ago" for twice daily

HOSTNAME=$(hostname)
DATE=$(date '+%Y-%m-%d')
TIME=$(date '+%H:%M:%S')

# Extract metrics from logs
get_reddit_stats() {
    journalctl -u reddit-fetcher.service --since "$REPORT_PERIOD" | \
    grep -E "Total new posts fetched|Successful subreddits" | \
    tail -6  # Last 6 runs (24hrs = 6 runs every 4hrs)
}

get_processing_stats() {
    journalctl -u content-processor.service --since "$REPORT_PERIOD" | \
    grep -E "Successfully processed|Failed to process" | \
    tail -6
}

get_error_count() {
    journalctl -u reddit-fetcher.service -u content-processor.service --since "$REPORT_PERIOD" -p err | wc -l
}

# Generate report
REDDIT_STATS=$(get_reddit_stats)
PROCESSING_STATS=$(get_processing_stats)
ERROR_COUNT=$(get_error_count)

# Calculate totals from logs
TOTAL_FETCHED=$(echo "$REDDIT_STATS" | grep -o "fetched: [0-9]*" | awk -F': ' '{sum+=$2} END {print sum+0}')
TOTAL_PROCESSED=$(echo "$PROCESSING_STATS" | grep -o "processed: [0-9]*" | awk -F': ' '{sum+=$2} END {print sum+0}')

EMAIL_SUBJECT="📊 AI Daily Digest Report - $DATE"
EMAIL_BODY="
AI Daily Digest - Daily Summary Report
=====================================

Server: $HOSTNAME
Date: $DATE $TIME
Period: Last 24 hours

📈 SUMMARY METRICS
==================
• Total Reddit posts fetched: $TOTAL_FETCHED
• Total posts processed: $TOTAL_PROCESSED  
• Errors encountered: $ERROR_COUNT

🔍 RECENT REDDIT FETCH RESULTS
===============================
$REDDIT_STATS

🧠 RECENT PROCESSING RESULTS  
=============================
$PROCESSING_STATS

📊 SYSTEM STATUS
================
Service Status:
$(systemctl is-active reddit-fetcher.timer) - Reddit Fetcher Timer
$(systemctl is-active content-processor.timer) - Content Processor Timer

Next Scheduled Runs:
$(systemctl list-timers reddit-fetcher.timer content-processor.timer --no-pager | head -4 | tail -2)

💾 RESOURCE USAGE
=================
$(free -h | head -2)
CPU: $(uptime | awk -F'load average:' '{print $2}')

--
Automated daily report from AI Daily Digest
Generated at $TIME on $DATE
"

# Send email (requires mailutils: sudo apt install mailutils postfix)
echo "$EMAIL_BODY" | mail -s "$EMAIL_SUBJECT" "$TO_EMAIL"

echo "Daily summary sent to $TO_EMAIL"