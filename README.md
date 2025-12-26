# Microsoft Forum Automation Bot

This bot automates the process of selecting checkboxes and clicking confirm on the Microsoft Forum page at https://ixpt.itechwx.com/MicrosoftForum.

## Features

- **Automatic CAPTCHA Reading**: Uses OCR (Tesseract) to automatically read canvas-based verification codes
- Automated login with username/password and verification code
- Handles the login page at https://ixpt.itechwx.com/login
- Selects all available checkboxes in the table
- Clicks the confirm button
- Runs continuously with configurable intervals
- 1-second delay between checkbox selections as requested
- Comprehensive logging
- Headless mode support
- Fallback to manual verification code input if OCR fails

## Installation

### Quick Setup
```bash
# Run the automated setup script
./run_bot.sh
```

### Manual Setup

1. **Install Tesseract OCR** (required for CAPTCHA reading):
```bash
./install_tesseract.sh
```

2. **Install Python dependencies**:
```bash
pip install -r requirements.txt
```

3. **Chrome WebDriver**:
   - The script will automatically download the appropriate ChromeDriver version
   - Make sure you have Google Chrome installed on your system

## Usage

### Basic Usage

#### Quick Start (Recommended)
For a simple one-time automation:
```bash
python quick_start.py
```

#### Full Bot
Run the bot with all options:
```bash
python forum_bot.py
```

The script will prompt you for:
- Username (defaults to "henry.mai")
- Password
- Whether to run in headless mode
- Interval between automation cycles (default: 60 seconds)
- Whether to run once or continuously

**Note**: The bot will automatically read the CAPTCHA using advanced OCR with multiple strategies. It will retry up to 5 times with different image processing techniques to ensure success.

### Command Line Options

You can also run the bot programmatically:

```python
from forum_bot import MicrosoftForumBot

# Initialize bot
bot = MicrosoftForumBot(headless=False)

try:
    bot.setup_driver()
    bot.login("henry.mai", "your_password")
    
    # Run single cycle
    bot.run_automation_cycle()
    
    # Or run continuously
    bot.run_continuous(interval=60)
    
finally:
    bot.close()
```

## Configuration

### Timing
- The bot waits 1 second between each checkbox selection as requested
- Configurable interval between complete automation cycles
- Default cycle interval is 60 seconds

### Browser Options
- Supports headless mode for running without GUI
- Configured for macOS with appropriate user agent
- Window size set to 1920x1080 for optimal compatibility

## How It Works

1. **Login**: 
   - Navigates to https://ixpt.itechwx.com/login
   - Enters username and password
   - **Automatically reads the canvas-based verification code using advanced OCR**
   - Uses 4 different image processing strategies and 6 OCR configurations
   - Retries up to 5 times with CAPTCHA refresh between attempts
   - Clicks the "Sign In" button
2. **Forum Navigation**: Redirects to the Microsoft Forum page
3. **Checkbox Selection**: Finds all checkboxes in the Ant Design table and selects them one by one with 1-second delays
4. **Confirm**: Clicks the confirm button after all checkboxes are selected
5. **Repeat**: Optionally repeats the process at specified intervals

## Troubleshooting

### Common Issues

1. **ChromeDriver not found**: Make sure Google Chrome is installed
2. **Login fails**: Verify credentials and check if the page structure has changed
3. **Elements not found**: The page structure may have changed; check the selectors in the code

### Logging

The bot provides detailed logging to help troubleshoot issues:
- INFO: Normal operations
- WARNING: Non-critical issues
- ERROR: Critical failures

## Security Notes

- Passwords are entered securely using getpass
- Consider using environment variables for credentials in production
- The bot respects the website's rate limiting with configurable delays

## Customization

You can modify the following in the code:
- Selectors for login form elements
- Checkbox selection logic
- Confirm button identification
- Timing intervals
- Browser options
