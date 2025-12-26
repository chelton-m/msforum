#!/bin/bash

echo "=== Chrome WebDriver Troubleshooting Script ==="
echo "This script will fix common Chrome hanging issues on macOS"
echo

# Step 1: Kill all Chrome processes
echo "Step 1: Killing all Chrome processes..."
killall "Google Chrome" 2>/dev/null || echo "No Chrome processes found"
killall "chromedriver" 2>/dev/null || echo "No chromedriver processes found"
sleep 2

# Step 2: Clear Chrome crash reports and logs
echo "Step 2: Clearing Chrome crash reports and logs..."
rm -rf ~/Library/Application\ Support/Google/Chrome/Crash\ Reports/* 2>/dev/null
rm -rf ~/Library/Logs/Google/Chrome/* 2>/dev/null
echo "Chrome logs cleared"

# Step 3: Remove Chrome lock files
echo "Step 3: Removing Chrome lock files..."
rm -f ~/Library/Application\ Support/Google/Chrome/SingletonLock 2>/dev/null
rm -f ~/Library/Application\ Support/Google/Chrome/*/SingletonLock 2>/dev/null
echo "Chrome lock files removed"

# Step 4: Check Chrome permissions
echo "Step 4: Checking Chrome permissions..."
if [ -d "/Applications/Google Chrome.app" ]; then
    echo "✅ Google Chrome is installed"
    
    # Check if Chrome is quarantined
    if xattr -l "/Applications/Google Chrome.app" | grep -q "com.apple.quarantine"; then
        echo "⚠️  Chrome is quarantined by macOS Gatekeeper"
        echo "Removing quarantine attribute..."
        sudo xattr -rd com.apple.quarantine "/Applications/Google Chrome.app"
        echo "✅ Quarantine removed"
    else
        echo "✅ Chrome is not quarantined"
    fi
else
    echo "❌ Google Chrome is not installed in /Applications/"
    echo "Please install Google Chrome first"
    exit 1
fi

# Step 5: Create clean Chrome profile
echo "Step 5: Creating clean Chrome profile for automation..."
AUTOMATION_PROFILE_DIR="$HOME/Library/Application Support/Google/Chrome/AutomationProfile"
if [ -d "$AUTOMATION_PROFILE_DIR" ]; then
    echo "Removing existing automation profile..."
    rm -rf "$AUTOMATION_PROFILE_DIR"
fi
mkdir -p "$AUTOMATION_PROFILE_DIR"
echo "✅ Clean automation profile created"

# Step 6: Test Chrome startup
echo "Step 6: Testing Chrome startup..."
echo "This will open Chrome briefly and close it..."
timeout 10s "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless --disable-gpu --no-sandbox --user-data-dir="$AUTOMATION_PROFILE_DIR" --remote-debugging-port=9222 &
CHROME_PID=$!
sleep 3
kill $CHROME_PID 2>/dev/null
wait $CHROME_PID 2>/dev/null

if [ $? -eq 0 ] || [ $? -eq 143 ]; then
    echo "✅ Chrome startup test successful"
else
    echo "❌ Chrome startup test failed"
    echo "You may need to manually allow Chrome in System Preferences > Security & Privacy"
fi

# Step 7: Check system resources
echo "Step 7: Checking system resources..."
FREE_RAM=$(vm_stat | grep "Pages free" | awk '{print $3}' | sed 's/\.//')
if [ "$FREE_RAM" -gt 100000 ]; then
    echo "✅ Sufficient free memory available"
else
    echo "⚠️  Low memory detected. Consider closing other applications"
fi

echo
echo "=== Chrome Fix Complete ==="
echo "Now try running your forum bot again:"
echo "cd /Users/henrymai/Chelton/msforum && source venv/bin/activate && python3 forum_bot.py"
echo


