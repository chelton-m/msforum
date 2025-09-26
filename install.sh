#!/bin/bash

# Microsoft Forum Bot Installation Script

echo "Installing Microsoft Forum Automation Bot..."
echo "============================================="

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed. Please install Python 3 first."
    exit 1
fi

# Check if pip is installed
if ! command -v pip3 &> /dev/null; then
    echo "Error: pip3 is not installed. Please install pip3 first."
    exit 1
fi

# Install Python dependencies
echo "Installing Python dependencies..."
pip3 install -r requirements.txt

# Check if Chrome is installed
if ! command -v google-chrome &> /dev/null && ! command -v chromium-browser &> /dev/null; then
    echo "Warning: Google Chrome is not installed. The bot requires Chrome to work."
    echo "Please install Google Chrome from: https://www.google.com/chrome/"
fi

# Make the script executable
chmod +x forum_bot.py

echo ""
echo "Installation completed!"
echo ""
echo "To run the bot:"
echo "  python3 forum_bot.py"
echo ""
echo "Make sure you have:"
echo "  1. Google Chrome installed"
echo "  2. Valid credentials for henry.mai"
echo "  3. Access to https://ixpt.itechwx.com/MicrosoftForum"
echo ""
