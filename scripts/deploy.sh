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

# Set correct permissions
echo -e "${BLUE}🔐 Setting permissions...${NC}"
sudo chmod 644 "$SYSTEMD_DIR/reddit-fetcher.service"
sudo chmod 644 "$SYSTEMD_DIR/reddit-fetcher.timer"
sudo chmod 644 "$SYSTEMD_DIR/content-processor.service"
sudo chmod 644 "$SYSTEMD_DIR/content-processor.timer"

# Reload systemd
echo -e "${BLUE}🔄 Reloading systemd...${NC}"
sudo systemctl daemon-reload

# Enable and start timers
echo -e "${BLUE}⏰ Enabling and starting timers...${NC}"
sudo systemctl enable reddit-fetcher.timer
sudo systemctl enable content-processor.timer
sudo systemctl start reddit-fetcher.timer
sudo systemctl start content-processor.timer

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
echo "Manual run:          sudo systemctl start reddit-fetcher.service"
echo "                     sudo systemctl start content-processor.service"
echo "Stop timers:         sudo systemctl stop reddit-fetcher.timer"
echo "                     sudo systemctl stop content-processor.timer"
echo "Check status:        sudo systemctl status reddit-fetcher.timer"
echo "List all timers:     sudo systemctl list-timers"

echo ""
echo -e "${GREEN}🎉 Your AI Daily Digest is now running automatically every 4 hours!${NC}"