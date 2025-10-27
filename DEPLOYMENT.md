# Microsoft Forum Bot Web Service Deployment Guide

This guide will help you deploy the Microsoft Forum Bot as a web service that can be accessed by other machines online.

## Quick Start Options

### Option 1: Local Development Server
```bash
# Install dependencies
pip install -r requirements-web.txt

# Run the web application
python app.py
```

The web interface will be available at: http://localhost:5000

### Option 2: Docker Deployment
```bash
# Build and run with Docker Compose
docker-compose up -d

# Or build and run manually
docker build -t msforum-bot .
docker run -p 5000:5000 msforum-bot
```

### Option 3: Cloud Deployment

## Cloud Platform Deployment

### Heroku Deployment

1. **Create Heroku App:**
```bash
# Install Heroku CLI
# Create new app
heroku create your-app-name

# Set environment variables
heroku config:set SECRET_KEY=your-secret-key-here
```

2. **Create Procfile:**
```bash
echo "web: gunicorn --bind 0.0.0.0:$PORT --workers 1 --timeout 300 app:app" > Procfile
```

3. **Deploy:**
```bash
git add .
git commit -m "Deploy to Heroku"
git push heroku main
```

### Railway Deployment

1. **Connect GitHub repository to Railway**
2. **Set environment variables:**
   - `SECRET_KEY`: Your secret key
3. **Deploy automatically**

### DigitalOcean App Platform

1. **Create new app from GitHub**
2. **Configure build settings:**
   - Build command: `pip install -r requirements-web.txt`
   - Run command: `gunicorn --bind 0.0.0.0:$PORT --workers 1 --timeout 300 app:app`
3. **Set environment variables**
4. **Deploy**

### AWS EC2 Deployment

1. **Launch EC2 instance (Ubuntu 20.04+)**
2. **Install dependencies:**
```bash
sudo apt update
sudo apt install python3-pip python3-venv nginx

# Install Chrome
wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | sudo apt-key add -
echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" | sudo tee /etc/apt/sources.list.d/google-chrome.list
sudo apt update
sudo apt install google-chrome-stable

# Install Tesseract
sudo apt install tesseract-ocr tesseract-ocr-eng
```

3. **Deploy application:**
```bash
# Clone your repository
git clone https://github.com/yourusername/msforum.git
cd msforum

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements-web.txt

# Run with Gunicorn
gunicorn --bind 0.0.0.0:5000 --workers 1 --timeout 300 app:app
```

4. **Configure Nginx (optional):**
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## Environment Variables

Set these environment variables for production:

- `SECRET_KEY`: Flask secret key for sessions
- `FLASK_ENV`: Set to `production` for production
- `PORT`: Port number (usually set by cloud platform)

## Security Considerations

1. **Change default credentials** in the web interface
2. **Use HTTPS** in production
3. **Set strong SECRET_KEY**
4. **Limit access** with authentication if needed
5. **Monitor logs** for suspicious activity

## API Endpoints

The web service provides these REST API endpoints:

- `GET /` - Web dashboard
- `GET /api/status` - Get bot status
- `POST /api/start` - Start bot monitoring
- `POST /api/stop` - Stop bot monitoring
- `POST /api/run-once` - Run single automation cycle
- `POST /api/login` - Test login credentials
- `GET /api/logs` - Get activity logs

## Usage

1. **Access the web interface** at your deployed URL
2. **Enter your Microsoft Forum credentials**
3. **Test login** to verify credentials work
4. **Start monitoring** to begin automated case processing
5. **Monitor activity** through the dashboard

## Troubleshooting

### Common Issues:

1. **Chrome/ChromeDriver issues:**
   - Ensure Chrome is installed
   - Check ChromeDriver compatibility

2. **Tesseract OCR issues:**
   - Install Tesseract: `sudo apt install tesseract-ocr`
   - Check Tesseract path in code

3. **Login failures:**
   - Verify credentials are correct
   - Check if CAPTCHA is required
   - Try manual login first

4. **Memory issues:**
   - Reduce worker count in Gunicorn
   - Monitor memory usage

### Logs:
Check application logs for detailed error information:
```bash
# Docker logs
docker logs container-name

# Heroku logs
heroku logs --tail

# System logs
journalctl -u your-service-name
```

## Scaling

For high-traffic deployments:

1. **Use multiple workers** (adjust Gunicorn workers)
2. **Add load balancer** (Nginx, CloudFlare)
3. **Use Redis** for session storage
4. **Monitor performance** and adjust resources

## Support

For issues or questions:
1. Check the logs first
2. Verify all dependencies are installed
3. Test with local deployment first
4. Check cloud platform documentation
