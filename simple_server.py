#!/usr/bin/env python3
"""
Simple server to run forum_bot.py directly - no Flask complications
"""
import subprocess
import threading
import time
import json
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse

# Global bot process
bot_process = None
bot_status = {
    'running': False,
    'last_check': None,
    'processed_cases': 0,
    'error_message': None
}

class BotHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            # Serve the HTML file
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            
            with open('index.html', 'r') as f:
                self.wfile.write(f.read().encode())
                
        elif self.path == '/bot-status':
            # Return bot status
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(bot_status).encode())
            
        else:
            self.send_response(404)
            self.end_headers()
    
    def do_POST(self):
        global bot_process, bot_status
        
        if self.path == '/run-bot':
            if bot_status['running']:
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': 'Bot already running'}).encode())
                return
            
            # Start forum_bot.py directly
            try:
                # Change to the directory where forum_bot.py is located
                os.chdir('/Users/henrymai/Chelton/work/msforum')
                
                # Run forum_bot.py with virtual environment
                cmd = "source venv/bin/activate && python forum_bot.py"
                bot_process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                
                bot_status['running'] = True
                bot_status['error_message'] = None
                bot_status['last_check'] = time.strftime('%H:%M:%S')
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'success': True}).encode())
                
                # Start monitoring thread
                threading.Thread(target=monitor_bot, daemon=True).start()
                
            except Exception as e:
                bot_status['running'] = False
                bot_status['error_message'] = str(e)
                
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': str(e)}).encode())
                
        elif self.path == '/stop-bot':
            if bot_process:
                bot_process.terminate()
                bot_process = None
            
            bot_status['running'] = False
            bot_status['last_check'] = time.strftime('%H:%M:%S')
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'success': True}).encode())
            
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        # Suppress default logging
        pass

def monitor_bot():
    """Monitor the bot process"""
    global bot_process, bot_status
    
    while bot_process and bot_process.poll() is None:
        time.sleep(2)
        bot_status['last_check'] = time.strftime('%H:%M:%S')
    
    # Process ended
    bot_status['running'] = False
    bot_status['last_check'] = time.strftime('%H:%M:%S')
    if bot_process:
        bot_status['error_message'] = 'Bot process ended'

if __name__ == '__main__':
    print("Starting simple bot server...")
    print("Open http://localhost:3001 in your browser")
    
    server = HTTPServer(('localhost', 3001), BotHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        if bot_process:
            bot_process.terminate()
        server.shutdown()
