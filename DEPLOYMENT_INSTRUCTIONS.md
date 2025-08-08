# CodeLearn LMS - Production Deployment Instructions

## 🚀 Deployment Package: `codelearn_lms_production.zip`

**Domain:** uptrail.ralfiz.com  
**File Size:** ~9.4MB  
**Location:** `../codelearn_lms_production.zip`

---

## 📋 Pre-Deployment Setup

### 1. Server Requirements
- Python 3.11+ 
- PostgreSQL (recommended) or MySQL
- Redis (optional, for caching)
- Web server (Apache/Nginx)

### 2. Upload and Extract
```bash
# Upload the zip file to your shared hosting
# Extract in your domain directory (usually public_html or www)
unzip codelearn_lms_production.zip
```

---

## 🔧 Configuration Steps

### 1. Environment Variables
Copy and configure the environment file:
```bash
cp .env.production .env
```

**Edit `.env` with your actual values:**
```bash
# CRITICAL: Change these values
SECRET_KEY=your-60-character-random-secret-key
DB_NAME=your_database_name
DB_USER=your_database_user  
DB_PASSWORD=your_database_password
DB_HOST=localhost

# Email Configuration
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-gmail-app-password

# Payment Gateway (Production)
RAZORPAY_KEY_ID=rzp_live_your_key_id
RAZORPAY_KEY_SECRET=your_razorpay_secret

# Optional Services
YOUTUBE_API_KEY=your_youtube_api_key
SENTRY_DSN=your_sentry_dsn
```

### 2. Database Setup
```bash
# Create PostgreSQL database (recommended)
createdb codelearn_lms_prod

# Or create MySQL database through your hosting panel
```

### 3. Python Virtual Environment
```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment  
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt
```

### 4. Django Setup
```bash
# Set production settings
export DJANGO_SETTINGS_MODULE=codelearn_lms.settings_production

# Run database migrations
python manage.py makemigrations
python manage.py migrate --settings=codelearn_lms.settings_production

# Collect static files
python manage.py collectstatic --noinput --settings=codelearn_lms.settings_production

# Create superuser (admin account)
python manage.py createsuperuser --settings=codelearn_lms.settings_production
```

---

## 🌐 Web Server Configuration

### For Shared Hosting (cPanel/DirectAdmin)
Most shared hosting providers support Python apps. Configure:

1. **Python App Setup:**
   - Set Python version: 3.11+
   - Set application root: `/home/username/public_html/`
   - Set startup file: `passenger_wsgi.py` (included in zip)

2. **Environment Variables:**
   Add in your hosting control panel:
   ```
   DJANGO_SETTINGS_MODULE=codelearn_lms.settings_production
   ```

### For VPS/Dedicated Server (Apache)
Create `.htaccess` file (sample included):
```apache
# Enable Python WSGI
PassengerEnabled On
PassengerAppRoot /path/to/your/project
PassengerPython /path/to/your/project/venv/bin/python
```

---

## 🔐 Security Checklist

- ✅ DEBUG = False
- ✅ Strong SECRET_KEY (60+ characters)
- ✅ HTTPS enabled (SSL certificate)
- ✅ Database password protected
- ✅ Admin URL secured (`/secure-admin/`)
- ✅ CORS configured for your domain
- ✅ Security headers enabled

---

## 📱 Access Points

After successful deployment:

- **Admin Panel:** `https://uptrail.ralfiz.com/admin/`
- **API Documentation:** `https://uptrail.ralfiz.com/api/docs/`
- **Health Check:** `https://uptrail.ralfiz.com/health/`

---

## 🐛 Troubleshooting

### Common Issues:

1. **ImportError: No module named 'apps'**
   - Ensure PYTHONPATH includes project directory
   - Check virtual environment is activated

2. **Database Connection Error**
   - Verify database credentials in `.env`
   - Ensure database exists and user has permissions

3. **Static Files Not Loading**
   - Run `collectstatic` command
   - Check web server static file configuration

4. **Permission Denied**
   - Set correct file permissions: `chmod 755`
   - Ensure web server can read files

### Debug Mode (Temporarily):
```bash
# Only for debugging - NEVER in production
DEBUG=True python manage.py runserver
```

---

## 📞 Support

For deployment assistance:
- Check Django logs: `logs/django.log`
- Check server error logs
- Verify all environment variables are set
- Test database connection

---

## 🔄 Updates

To update the application:
1. Upload new version
2. Run migrations: `python manage.py migrate`
3. Collect static files: `python manage.py collectstatic`
4. Restart application (touch `tmp/restart.txt`)

**Production Settings Location:** `codelearn_lms/settings_production.py`