# Railway Deployment Guide for Lyceum LMS 🚂

## ✅ Repository Setup Complete!

**GitHub Repository:** https://github.com/jobinsebastianralfiz/lyceum_lms

The code has been successfully pushed to GitHub and is ready for Railway deployment!

---

## 🚀 Step 1: Deploy to Railway

### Option A: One-Click Deploy (Recommended)

1. **Go to Railway**: https://railway.app/
2. **Sign in** with your GitHub account
3. **Click "New Project"**
4. **Select "Deploy from GitHub repo"**
5. **Choose** `jobinsebastianralfiz/lyceum_lms`
6. **Railway will automatically**:
   - Detect the Django project
   - Use the `Procfile` for deployment
   - Use `runtime.txt` for Python version
   - Use `railway.toml` for configuration

### Option B: Railway CLI

```bash
# Install Railway CLI
npm i -g @railway/cli

# Login to Railway
railway login

# Initialize project
railway init

# Link to GitHub repo
railway link

# Deploy
railway up
```

---

## 🗄️ Step 2: Add PostgreSQL Database

1. **In Railway Dashboard**:
   - Click on your project
   - Click **"New"** → **"Database"** → **"PostgreSQL"**
   - Railway will automatically:
     - Create a PostgreSQL database
     - Add `DATABASE_URL` environment variable
     - Connect it to your Django app

2. **Important**: Railway provides `DATABASE_URL` automatically. Don't set it manually!

---

## 🔐 Step 3: Set Environment Variables

Go to **Railway Dashboard → Your Project → Variables** and add these:

### Required Variables:

```bash
# Django Settings
SECRET_KEY=your-super-secret-key-50-chars-min
DEBUG=False
ALLOWED_HOSTS=*.railway.app,yourdomain.com

# Database - DO NOT SET THIS! Railway provides it automatically
# DATABASE_URL is auto-provided by Railway PostgreSQL

# Django Settings Module
DJANGO_SETTINGS_MODULE=codelearn_lms.settings
PYTHONUNBUFFERED=1
```

### Email Settings (Required for notifications):

```bash
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-gmail-app-password
DEFAULT_FROM_EMAIL=Lyceum LMS <your-email@gmail.com>
```

**Get Gmail App Password**:
1. Go to https://myaccount.google.com/security
2. Enable 2-Factor Authentication
3. Go to "App passwords"
4. Generate password for "Mail"
5. Use that password in `EMAIL_HOST_PASSWORD`

### Payment Gateway (Razorpay):

```bash
RAZORPAY_KEY_ID=rzp_live_xxxxx
RAZORPAY_KEY_SECRET=your_secret_key
```

Get from: https://dashboard.razorpay.com/app/keys

### Media Files (Cloudinary - Recommended):

```bash
CLOUDINARY_CLOUD_NAME=your_cloud_name
CLOUDINARY_API_KEY=your_api_key
CLOUDINARY_API_SECRET=your_api_secret
```

**Setup Cloudinary**:
1. Sign up at https://cloudinary.com/
2. Go to Dashboard
3. Copy Cloud Name, API Key, API Secret
4. Add to Railway

### CORS Settings (For Flutter App):

```bash
CORS_ALLOWED_ORIGINS=https://your-flutter-app.com,https://yourdomain.com
CORS_ALLOW_CREDENTIALS=True
```

### JWT Settings:

```bash
SIMPLE_JWT_ACCESS_TOKEN_LIFETIME_MINUTES=60
SIMPLE_JWT_REFRESH_TOKEN_LIFETIME_DAYS=7
```

### Optional - Frontend URL:

```bash
FRONTEND_URL=https://your-flutter-app.com
```

---

## 🔧 Step 4: Update Django Settings for Production

The current `settings.py` needs updates. Add this to handle Railway's PostgreSQL:

```python
# At the top of settings.py
import dj_database_url

# Replace the DATABASES section with:
DATABASES = {
    'default': dj_database_url.config(
        default='sqlite:///db.sqlite3',
        conn_max_age=600
    )
}

# Static files for production
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATIC_URL = '/static/'

# Whitenoise for static files
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # Add this
    # ... rest of middleware
]

STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Security settings for production
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'
```

Add to `requirements.txt`:
```
dj-database-url==2.1.0
whitenoise==6.6.0
```

---

## 📋 Step 5: Post-Deployment Tasks

### 1. Run Migrations

Railway automatically runs migrations via the `Procfile`:
```
release: python manage.py migrate --noinput
```

If you need to run them manually:
```bash
railway run python manage.py migrate
```

### 2. Create Superuser

```bash
railway run python manage.py createsuperuser
```

### 3. Collect Static Files

```bash
railway run python manage.py collectstatic --noinput
```

---

## 🌐 Step 6: Get Your Deployment URL

1. **Railway will provide a URL** like: `https://lyceum-lms-production.up.railway.app`
2. **Test your API**: `https://your-app.railway.app/api/`
3. **Admin panel**: `https://your-app.railway.app/admin/`

---

## 🔄 Step 7: Update Flutter App

Update your Flutter app's API base URL to point to Railway:

```dart
// lib/services/api_config.dart
class ApiConfig {
  static const String baseUrl = 'https://lyceum-lms-production.up.railway.app';
  static const String apiUrl = '$baseUrl/api';
}
```

---

## 🎯 Step 8: Custom Domain (Optional)

1. **In Railway Dashboard**:
   - Go to your project
   - Click **"Settings"** → **"Domains"**
   - Click **"Add Domain"**
   - Enter your domain (e.g., `api.lyceumlms.com`)

2. **Update DNS** (at your domain registrar):
   - Add CNAME record:
     - Name: `api` (or `@` for root)
     - Value: `your-app.up.railway.app`

3. **Update ALLOWED_HOSTS**:
   ```bash
   ALLOWED_HOSTS=*.railway.app,api.lyceumlms.com,lyceumlms.com
   ```

---

## 📊 Monitoring & Logs

### View Logs:
```bash
railway logs
```

Or in Railway Dashboard → Your Project → **"Deployments"** → Click on deployment → **"Logs"**

### Monitor Performance:
- Railway Dashboard shows CPU, Memory, Network usage
- Check **"Metrics"** tab in your project

---

## 🔒 Security Checklist

- ✅ `DEBUG=False` in production
- ✅ Strong `SECRET_KEY` (50+ random characters)
- ✅ `ALLOWED_HOSTS` configured correctly
- ✅ HTTPS enabled (Railway provides automatically)
- ✅ CORS configured for your Flutter app only
- ✅ Database credentials secured (Railway handles this)
- ✅ Cloudinary for media files (not local storage)
- ✅ Gmail App Password (not regular password)
- ✅ Razorpay live keys (not test keys)

---

## 🐛 Troubleshooting

### Issue: Migrations not running
```bash
railway run python manage.py migrate
```

### Issue: Static files not loading
```bash
railway run python manage.py collectstatic --noinput
```

### Issue: 500 Error
- Check logs: `railway logs`
- Ensure `DEBUG=False`
- Check `ALLOWED_HOSTS` includes your Railway domain

### Issue: Database connection error
- Railway should provide `DATABASE_URL` automatically
- Don't set `DATABASE_URL` manually
- Check PostgreSQL service is added to project

### Issue: CORS errors from Flutter
- Add your Flutter app domain to `CORS_ALLOWED_ORIGINS`
- Make sure it starts with `https://`

---

## 📚 Additional Resources

- **Railway Docs**: https://docs.railway.app/
- **Django Deployment Checklist**: https://docs.djangoproject.com/en/5.0/howto/deployment/checklist/
- **Cloudinary Django**: https://cloudinary.com/documentation/django_integration

---

## 🎉 You're Done!

Your Lyceum LMS backend is now deployed on Railway!

**Next Steps**:
1. Test all API endpoints
2. Update Flutter app with new API URL
3. Test payment gateway in live mode
4. Monitor logs for any errors
5. Set up automatic backups (Railway provides this)

**Repository**: https://github.com/jobinsebastianralfiz/lyceum_lms
**Railway**: https://railway.app/

Happy coding! 🚀
