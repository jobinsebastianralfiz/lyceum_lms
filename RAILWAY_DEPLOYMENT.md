# Railway Deployment Guide for Lyceum LMS

## Prerequisites
- GitHub account
- Railway account (sign up at railway.app)
- PostgreSQL database (Railway provides this)

## Environment Variables for Railway

Set these in Railway Dashboard → Your Project → Variables:

```bash
# Django Settings
SECRET_KEY=your-super-secret-key-generate-a-new-one
DEBUG=False
ALLOWED_HOSTS=*.railway.app,yourdomain.com

# Database (Railway will provide DATABASE_URL automatically)
# Don't set DATABASE_URL manually - Railway provides it

# Email Settings (update with your SMTP details)
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password

# Payment Gateway (Razorpay)
RAZORPAY_KEY_ID=your_razorpay_key
RAZORPAY_KEY_SECRET=your_razorpay_secret

# Media Files (Use Cloudinary or S3 for production)
# Cloudinary Settings
CLOUDINARY_CLOUD_NAME=your_cloud_name
CLOUDINARY_API_KEY=your_api_key
CLOUDINARY_API_SECRET=your_api_secret

# CORS Settings
CORS_ALLOWED_ORIGINS=https://your-flutter-app.com,https://yourdomain.com

# JWT Settings
SIMPLE_JWT_ACCESS_TOKEN_LIFETIME_MINUTES=60
SIMPLE_JWT_REFRESH_TOKEN_LIFETIME_DAYS=7

# Other Settings
DJANGO_SETTINGS_MODULE=codelearn_lms.settings
PYTHONUNBUFFERED=1
