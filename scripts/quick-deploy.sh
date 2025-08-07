#!/bin/bash

# Quick Deploy Script - Automates the common deployment steps
# Equivalent to the manual commands you just ran

set -e

SCRIPTS_DIR="/opt/aidaily-digest/scripts"
SYSTEMD_DIR="/etc/systemd/system"

echo "🚀 Quick Deploy - Updating systemd services"
echo "==========================================="

# Navigate to project directory
cd "$SCRIPTS_DIR"

echo "📋 Copying service files..."
sudo cp systemd/content-processor.service /etc/systemd/system/
sudo cp systemd/reddit-fetcher.service /etc/systemd/system/

echo "🔄 Reloading systemd..."
sudo systemctl daemon-reload

echo "🔄 Restarting timers..."
sudo systemctl restart content-processor.timer
sudo systemctl restart reddit-fetcher.timer

echo "✅ Quick deploy completed!"
echo ""
echo "📊 Service Status:"
systemctl is-active reddit-fetcher.timer && echo "  ✅ Reddit Fetcher: Active" || echo "  ❌ Reddit Fetcher: Inactive"
systemctl is-active content-processor.timer && echo "  ✅ Content Processor: Active" || echo "  ❌ Content Processor: Inactive"

echo ""
echo "🔍 To check logs:"
echo "  sudo journalctl -u reddit-fetcher.service -f"
echo "  sudo journalctl -u content-processor.service -f"