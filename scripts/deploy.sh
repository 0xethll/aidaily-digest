#!/bin/bash
set -e

# AI Daily Digest Deployment Script
# This script sets up the systemd services and timers for automated execution

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_DIR="/opt/aidaily-digest"
SCRIPTS_DIR="$PROJECT_DIR/scripts"
SYSTEMD_DIR="/etc/systemd/system"
SERVICE_USER="asher"

echo -e "${BLUE}🚀 AI Daily Digest Deployment Script${NC}"
echo "=================================================="

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   echo -e "${RED}❌ This script should not be run as root${NC}"
   echo "Run it as your regular user (it will use sudo when needed)"
   exit 1
fi

# Check if project directory exists
if [ ! -d "$SCRIPTS_DIR" ]; then
    echo -e "${RED}❌ Project directory not found: $SCRIPTS_DIR${NC}"
    echo "Please ensure the project is cloned to $PROJECT_DIR"
    exit 1
fi

# Check if systemd files exist
if [ ! -f "$SCRIPTS_DIR/systemd/reddit-fetcher.service" ]; then
    echo -e "${RED}❌ Systemd service files not found${NC}"
    echo "Please ensure systemd files are in $SCRIPTS_DIR/systemd/"
    exit 1
fi

# Update service files with correct user
echo -e "${BLUE}🔧 Updating service files with user: $SERVICE_USER${NC}"
sed -i "s/User=ubuntu/User=$SERVICE_USER/g" "$SCRIPTS_DIR/systemd/"*.service
sed -i "s/Group=ubuntu/Group=$SERVICE_USER/g" "$SCRIPTS_DIR/systemd/"*.service

# Copy systemd files
echo -e "${BLUE}📋 Copying systemd files...${NC}"
sudo cp "$SCRIPTS_DIR/systemd/reddit-fetcher.service" "$SYSTEMD_DIR/"
sudo cp "$SCRIPTS_DIR/systemd/reddit-fetcher.timer" "$SYSTEMD_DIR/"
sudo cp "$SCRIPTS_DIR/systemd/content-processor.service" "$SYSTEMD_DIR/"
sudo cp "$SCRIPTS_DIR/systemd/content-processor.timer" "$SYSTEMD_DIR/"

# Copy optional services if they exist
if [ -f "$SCRIPTS_DIR/systemd/webhook-summary.service" ]; then
    sudo cp "$SCRIPTS_DIR/systemd/webhook-summary.service" "$SYSTEMD_DIR/"
    sudo cp "$SCRIPTS_DIR/systemd/webhook-summary.timer" "$SYSTEMD_DIR/"
fi

if [ -f "$SCRIPTS_DIR/systemd/daily-summary.service" ]; then
    sudo cp "$SCRIPTS_DIR/systemd/daily-summary.service" "$SYSTEMD_DIR/"
    sudo cp "$SCRIPTS_DIR/systemd/daily-summary.timer" "$SYSTEMD_DIR/"
fi

if [ -f "$SCRIPTS_DIR/systemd/twitter-poster.service" ]; then
    sudo cp "$SCRIPTS_DIR/systemd/twitter-poster.service" "$SYSTEMD_DIR/"
    sudo cp "$SCRIPTS_DIR/systemd/twitter-poster.timer" "$SYSTEMD_DIR/"
fi

# Set correct permissions
echo -e "${BLUE}🔐 Setting permissions...${NC}"
sudo chmod 644 "$SYSTEMD_DIR/"*.service 2>/dev/null || true
sudo chmod 644 "$SYSTEMD_DIR/"*.timer 2>/dev/null || true

# Reload systemd
echo -e "${BLUE}🔄 Reloading systemd...${NC}"
sudo systemctl daemon-reload

# Enable and start main timers
echo -e "${BLUE}⏰ Enabling and starting main timers...${NC}"
sudo systemctl enable reddit-fetcher.timer
sudo systemctl enable content-processor.timer
sudo systemctl start reddit-fetcher.timer
sudo systemctl start content-processor.timer

# Enable optional timers if they exist
if [ -f "$SYSTEMD_DIR/webhook-summary.timer" ]; then
    echo -e "${BLUE}📡 Enabling webhook notifications...${NC}"
    sudo systemctl enable webhook-summary.timer
    sudo systemctl start webhook-summary.timer
fi

if [ -f "$SYSTEMD_DIR/daily-summary.timer" ]; then
    echo -e "${BLUE}📧 Enabling email notifications...${NC}"
    sudo systemctl enable daily-summary.timer
    sudo systemctl start daily-summary.timer
fi

if [ -f "$SYSTEMD_DIR/twitter-poster.timer" ]; then
    echo -e "${BLUE}🐦 Enabling Twitter posting...${NC}"
    sudo systemctl enable twitter-poster.timer
    sudo systemctl start twitter-poster.timer
fi

# Show status
echo -e "${GREEN}✅ Deployment completed successfully!${NC}"
echo ""
echo -e "${YELLOW}📊 Current Status:${NC}"
sudo systemctl status reddit-fetcher.timer --no-pager -l
echo ""
sudo systemctl status content-processor.timer --no-pager -l

echo ""
echo -e "${YELLOW}📅 Next scheduled runs:${NC}"
sudo systemctl list-timers reddit-fetcher.timer content-processor.timer --no-pager

echo ""
echo -e "${YELLOW}🛠️  Useful Commands:${NC}"
echo "View logs:           sudo journalctl -u reddit-fetcher.service -f"
echo "                     sudo journalctl -u content-processor.service -f"
echo "                     sudo journalctl -u webhook-summary.service -f"
echo "                     sudo journalctl -u daily-summary.service -f"
echo "                     sudo journalctl -u twitter-poster.service -f"
echo "Manual run:          sudo systemctl start reddit-fetcher.service"
echo "                     sudo systemctl start content-processor.service"
echo "                     sudo systemctl start webhook-summary.service"
echo "                     sudo systemctl start daily-summary.service"
echo "                     sudo systemctl start twitter-poster.service"
echo "Stop timers:         sudo systemctl stop reddit-fetcher.timer"
echo "                     sudo systemctl stop content-processor.timer"
echo "                     sudo systemctl stop webhook-summary.timer"
echo "                     sudo systemctl stop daily-summary.timer"
echo "                     sudo systemctl stop twitter-poster.timer"
echo "Check status:        sudo systemctl status reddit-fetcher.timer"
echo "List all timers:     sudo systemctl list-timers"

echo ""
echo -e "${GREEN}🎉 Your AI Daily Digest is now running automatically every 4 hours!${NC}"