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
from forum_bot import MicrosoftForumBot

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
    """Start the bot monitoring"""
    global bot_instance, monitoring_thread, bot_status
    
    try:
        if bot_status['running']:
            return jsonify({'success': False, 'message': 'Bot is already running'})
        
        # Get credentials from request
        data = request.get_json()
        username = data.get('username', 'henry.mai')
        password = data.get('password', 'abc@123456')
        
        # Initialize bot
        bot_instance = MicrosoftForumBot(headless=True)  # Run headless for web service
        bot_instance.setup_driver()
        
        # Attempt login
        login_success = bot_instance.login(username, password)
        
        if not login_success:
            update_bot_status({
                'running': False,
                'error_message': 'Login failed. Please check credentials.',
                'login_status': False
            })
            return jsonify({'success': False, 'message': 'Login failed'})
        
        update_bot_status({
            'running': True,
            'error_message': None,
            'login_status': True,
            'processed_cases': 0
        })
        
        # Start monitoring in background thread
        def monitor():
            try:
                bot_instance.continuous_monitor(interval_seconds=30)  # Check every 30 seconds
            except Exception as e:
                logger.error(f"Monitoring error: {e}")
                update_bot_status({
                    'running': False,
                    'error_message': str(e)
                })
        
        monitoring_thread = threading.Thread(target=monitor, daemon=True)
        monitoring_thread.start()
        
        return jsonify({'success': True, 'message': 'Bot started successfully'})
        
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
    """Run a single automation cycle"""
    global bot_instance
    
    try:
        if not bot_instance:
            return jsonify({'success': False, 'message': 'Bot not initialized. Please start the bot first.'})
        
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
    """Test login with provided credentials"""
    global bot_instance
    
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return jsonify({'success': False, 'message': 'Username and password required'})
        
        # Create temporary bot instance for login test
        temp_bot = MicrosoftForumBot(headless=True)
        temp_bot.setup_driver()
        
        login_success = temp_bot.login(username, password)
        temp_bot.close()
        
        if login_success:
            return jsonify({'success': True, 'message': 'Login successful'})
        else:
            return jsonify({'success': False, 'message': 'Login failed'})
            
    except Exception as e:
        logger.error(f"Error testing login: {e}")
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
    app.run(host='0.0.0.0', port=5000, debug=True)
