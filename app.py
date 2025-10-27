#!/usr/bin/env python3
"""
Microsoft Forum Bot Web Service
A Flask web application that provides REST API and web interface for the Microsoft Forum automation bot.
"""

from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import threading
import time
import logging
from datetime import datetime
import os
try:
    from forum_bot import MicrosoftForumBot
    from selenium.webdriver.common.by import By
except ImportError as e:
    print(f"Warning: Could not import forum_bot: {e}")
    MicrosoftForumBot = None

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key-change-this')

# Global bot instance and status
bot_instance = None
bot_status = {
    'running': False,
    'last_check': None,
    'total_cases': 0,
    'processed_cases': 0,
    'error_message': None,
    'login_status': False
}

# Bot monitoring thread
monitoring_thread = None

def update_bot_status(status_update):
    """Update bot status safely"""
    global bot_status
    bot_status.update(status_update)
    bot_status['last_check'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('index.html', status=bot_status)

@app.route('/api/status')
def api_status():
    """Get current bot status"""
    return jsonify(bot_status)

@app.route('/api/start', methods=['POST'])
def api_start():
    """Start bot - runs forum_bot.py directly"""
    global bot_instance, monitoring_thread, bot_status
    
    try:
        if bot_status['running']:
            return jsonify({'success': False, 'message': 'Bot is already running'})
        
        # Get credentials from request
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return jsonify({'success': False, 'message': 'Username and password required'})
        
        update_bot_status({
            'running': True,
            'error_message': None,
            'login_status': False,
            'processed_cases': 0
        })
        
        # Run forum_bot.py exactly like manual execution
        def run_forum_bot():
            global bot_instance
            try:
                # Use the MicrosoftForumBot class directly
                if MicrosoftForumBot is None:
                    update_bot_status({
                        'running': False,
                        'error_message': 'Bot module not available'
                    })
                    return
                
                # Create bot instance with visible browser (like forum_bot.py main())
                bot_instance = MicrosoftForumBot(headless=False)
                bot_instance.setup_driver()
                
                # Navigate to login page and auto-fill username/password
                login_url = "https://ixpt.itechwx.com/login"
                logger.info(f"Navigating to login page: {login_url}")
                bot_instance.driver.get(login_url)
                time.sleep(5)  # Wait longer for page to load
                
                # Auto-fill username and password with better selectors
                try:
                    # Wait for page to load completely
                    time.sleep(3)
                    
                    # Try multiple selectors for username field (same as forum_bot.py)
                    username_selectors = [
                        "input[placeholder*='account']",
                        "input[placeholder*='Account']", 
                        "input[name='username']",
                        "input[name='account']",
                        "input[type='text']",
                        "input[placeholder*='Please input account']",
                        "input[placeholder*='please input account']"
                    ]
                    
                    username_field = None
                    logger.info("Looking for username field...")
                    for selector in username_selectors:
                        try:
                            elements = bot_instance.driver.find_elements(By.CSS_SELECTOR, selector)
                            logger.info(f"Found {len(elements)} elements with username selector: {selector}")
                            for element in elements:
                                if element.is_displayed():
                                    username_field = element
                                    logger.info(f"✅ Found username field with selector: {selector}")
                                    break
                            if username_field:
                                break
                        except Exception as e:
                            logger.warning(f"Selector {selector} failed: {e}")
                            continue
                    
                    # Try multiple selectors for password field
                    password_selectors = [
                        "input[placeholder*='password']",
                        "input[placeholder*='Password']",
                        "input[name='password']", 
                        "input[type='password']",
                        "input[placeholder*='Please input password']",
                        "input[placeholder*='please input password']"
                    ]
                    
                    password_field = None
                    logger.info("Looking for password field...")
                    for selector in password_selectors:
                        try:
                            elements = bot_instance.driver.find_elements(By.CSS_SELECTOR, selector)
                            logger.info(f"Found {len(elements)} elements with password selector: {selector}")
                            for element in elements:
                                if element.is_displayed():
                                    password_field = element
                                    logger.info(f"✅ Found password field with selector: {selector}")
                                    break
                            if password_field:
                                break
                        except Exception as e:
                            logger.warning(f"Selector {selector} failed: {e}")
                            continue
                    
                    # Fill the fields if found
                    if username_field and password_field:
                        logger.info("Filling username...")
                        username_field.clear()
                        username_field.send_keys(username)
                        
                        logger.info("Filling password...")
                        password_field.clear()
                        password_field.send_keys(password)
                        
                        logger.info("✅ Username and password filled automatically")
                    else:
                        logger.warning("❌ Could not find username or password fields")
                        # Debug: list all input elements
                        try:
                            all_inputs = bot_instance.driver.find_elements(By.TAG_NAME, "input")
                            logger.info(f"Found {len(all_inputs)} input elements total:")
                            for i, inp in enumerate(all_inputs):
                                if inp.is_displayed():
                                    placeholder = inp.get_attribute('placeholder')
                                    name = inp.get_attribute('name')
                                    input_type = inp.get_attribute('type')
                                    logger.info(f"  Input {i+1}: type='{input_type}', name='{name}', placeholder='{placeholder}'")
                        except Exception as e:
                            logger.warning(f"Error listing inputs: {e}")
                            
                except Exception as e:
                    logger.error(f"Error auto-filling credentials: {e}")
                
                # Try to auto-login first, if fails then wait for manual input
                logger.info("Trying to auto-login...")
                
                # Look for login button and try to click it
                try:
                    login_button_selectors = [
                        "//button[contains(text(), 'Sign In')]",
                        "//input[@value='Sign In']",
                        "//button[@type='submit']",
                        "//input[@type='submit']",
                        "//button[contains(text(), 'Login')]",
                        "//button[contains(text(), '登录')]",
                        "button[type='submit']",
                        "input[type='submit']"
                    ]
                    
                    login_button = None
                    for selector in login_button_selectors:
                        try:
                            if selector.startswith("//"):
                                login_button = bot_instance.driver.find_element(By.XPATH, selector)
                            else:
                                login_button = bot_instance.driver.find_element(By.CSS_SELECTOR, selector)
                            break
                        except:
                            continue
                    
                    if login_button:
                        logger.info("Clicking login button...")
                        login_button.click()
                        time.sleep(3)
                        
                        # Check if login was successful
                        current_url = bot_instance.driver.current_url
                        if "MicrosoftForum" in current_url or "login" not in current_url:
                            logger.info("✅ Auto-login successful!")
                        else:
                            logger.info("Auto-login failed, waiting for manual CAPTCHA input...")
                            # Wait briefly for manual input
                            time.sleep(10)  # Give user 10 seconds to enter CAPTCHA
                    else:
                        logger.info("No login button found, waiting for manual input...")
                        time.sleep(10)  # Give user 10 seconds
                        
                except Exception as e:
                    logger.warning(f"Auto-login attempt failed: {e}")
                    time.sleep(10)  # Give user 10 seconds
                
                # Start continuous monitoring (like forum_bot.py main())
                logger.info("Starting continuous monitoring with 1 second intervals...")
                bot_instance.continuous_monitor(interval_seconds=1)
                
            except Exception as e:
                logger.error(f"Error running forum_bot: {e}")
                update_bot_status({
                    'running': False,
                    'error_message': str(e)
                })
        
        monitoring_thread = threading.Thread(target=run_forum_bot, daemon=True)
        monitoring_thread.start()
        
        return jsonify({'success': True, 'message': 'Forum bot started - check browser window for CAPTCHA input'})
        
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
        update_bot_status({
            'running': False,
            'error_message': str(e)
        })
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/stop', methods=['POST'])
def api_stop():
    """Stop the bot monitoring"""
    global bot_instance, bot_status
    
    try:
        if bot_instance:
            bot_instance.close()
            bot_instance = None
        
        update_bot_status({
            'running': False,
            'error_message': None
        })
        
        return jsonify({'success': True, 'message': 'Bot stopped successfully'})
        
    except Exception as e:
        logger.error(f"Error stopping bot: {e}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/run-once', methods=['POST'])
def api_run_once():
    """Run a single automation cycle - follows forum_bot.py run_automation_cycle exactly"""
    global bot_instance
    
    try:
        if not bot_instance:
            return jsonify({'success': False, 'message': 'Bot not initialized. Please start the bot first.'})
        
        # Follow exact logic from forum_bot.py run_automation_cycle method
        success = bot_instance.run_automation_cycle()
        
        if success:
            return jsonify({'success': True, 'message': 'Automation cycle completed successfully'})
        else:
            return jsonify({'success': False, 'message': 'Automation cycle failed'})
            
    except Exception as e:
        logger.error(f"Error running automation cycle: {e}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/login', methods=['POST'])
def api_login():
    """Test login with provided credentials - shows browser for manual CAPTCHA"""
    global bot_instance
    
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return jsonify({'success': False, 'message': 'Username and password required'})
        
        # Create temporary bot instance for login test with visible browser
        temp_bot = MicrosoftForumBot(headless=False)
        temp_bot.setup_driver()
        
        # Navigate to login page and show browser
        login_url = "https://ixpt.itechwx.com/login"
        temp_bot.driver.get(login_url)
        
        return jsonify({
            'success': True, 
            'message': 'Browser opened. Please enter CAPTCHA manually in the browser window.',
            'browser_open': True
        })
            
    except Exception as e:
        logger.error(f"Error opening login page: {e}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/complete-login', methods=['POST'])
def api_complete_login():
    """Complete login after manual CAPTCHA entry"""
    global bot_instance
    
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        captcha = data.get('captcha')
        
        if not username or not password or not captcha:
            return jsonify({'success': False, 'message': 'Username, password, and CAPTCHA required'})
        
        # Use existing bot instance or create new one
        if not bot_instance:
            bot_instance = MicrosoftForumBot(headless=False)
            bot_instance.setup_driver()
        
        login_success = bot_instance.login(username, password, captcha)
        
        if login_success:
            return jsonify({'success': True, 'message': 'Login successful'})
        else:
            return jsonify({'success': False, 'message': 'Login failed - check CAPTCHA'})
            
    except Exception as e:
        logger.error(f"Error completing login: {e}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/command', methods=['POST'])
def api_command():
    """Execute custom commands on the bot"""
    global bot_instance
    
    try:
        data = request.get_json()
        command = data.get('command', '').strip().lower()
        parameters = data.get('parameters', {})
        
        if not bot_instance:
            return jsonify({'success': False, 'message': 'Bot not initialized. Please start the bot first.'})
        
        # Handle different commands
        if command == 'check_cases':
            # Check for new cases
            cases_found = bot_instance.check_for_new_cases()
            return jsonify({
                'success': True, 
                'message': f'Found {cases_found} new cases',
                'data': {'cases_found': cases_found}
            })
        
        elif command == 'process_case':
            # Process a specific case
            case_id = parameters.get('case_id')
            if not case_id:
                return jsonify({'success': False, 'message': 'Case ID required'})
            
            success = bot_instance.process_specific_case(case_id)
            return jsonify({
                'success': success,
                'message': f'Case {case_id} processed successfully' if success else f'Failed to process case {case_id}'
            })
        
        elif command == 'get_status':
            # Get detailed status
            return jsonify({
                'success': True,
                'message': 'Status retrieved',
                'data': {
                    'running': bot_status['running'],
                    'login_status': bot_status['login_status'],
                    'total_cases': bot_status['total_cases'],
                    'processed_cases': bot_status['processed_cases'],
                    'last_check': bot_status['last_check']
                }
            })
        
        elif command == 'custom_action':
            # Execute custom automation action
            action = parameters.get('action')
            if not action:
                return jsonify({'success': False, 'message': 'Action parameter required'})
            
            # You can add more custom actions here
            if action == 'refresh_page':
                bot_instance.driver.refresh()
                return jsonify({'success': True, 'message': 'Page refreshed'})
            elif action == 'take_screenshot':
                screenshot = bot_instance.driver.get_screenshot_as_base64()
                return jsonify({'success': True, 'message': 'Screenshot taken', 'data': {'screenshot': screenshot}})
            else:
                return jsonify({'success': False, 'message': f'Unknown action: {action}'})
        
        else:
            return jsonify({'success': False, 'message': f'Unknown command: {command}'})
            
    except Exception as e:
        logger.error(f"Error executing command: {e}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/toggle-browser', methods=['POST'])
def api_toggle_browser():
    """Toggle browser visibility"""
    global bot_instance
    
    try:
        if not bot_instance:
            return jsonify({'success': False, 'message': 'Bot not initialized. Please start the bot first.'})
        
        # Toggle browser window visibility
        if hasattr(bot_instance.driver, 'minimize_window'):
            bot_instance.driver.minimize_window()
            return jsonify({'success': True, 'message': 'Browser minimized'})
        else:
            return jsonify({'success': True, 'message': 'Browser visibility toggled'})
            
    except Exception as e:
        logger.error(f"Error toggling browser: {e}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/logs')
def api_logs():
    """Get recent log entries"""
    # This is a simple implementation - in production you'd want proper log management
    return jsonify({
        'logs': [
            f"{datetime.now().strftime('%H:%M:%S')} - Bot status: {'Running' if bot_status['running'] else 'Stopped'}",
            f"{datetime.now().strftime('%H:%M:%S')} - Last check: {bot_status['last_check'] or 'Never'}",
            f"{datetime.now().strftime('%H:%M:%S')} - Total cases: {bot_status['total_cases']}",
            f"{datetime.now().strftime('%H:%M:%S')} - Processed cases: {bot_status['processed_cases']}"
        ]
    })

if __name__ == '__main__':
    # Create templates directory if it doesn't exist
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static', exist_ok=True)
    
    # Run the Flask app
    app.run(host='0.0.0.0', port=5001, debug=True)
