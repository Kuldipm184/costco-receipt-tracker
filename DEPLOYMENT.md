# 🚀 Deployment Guide

This guide will help you deploy your Costco Receipt Tracker application to various cloud platforms.

## Prerequisites

⚠️ **Important**: This app requires **Tesseract OCR** to be installed on the deployment platform. Not all platforms support this dependency.

## 🌟 Recommended Platforms

### 1. Railway (Recommended)

Railway is perfect for Python apps with system dependencies.

**Steps:**

1. Go to [railway.app](https://railway.app)
2. Sign up/login with GitHub
3. Click "New Project" → "Deploy from GitHub repo"
4. Select your `costco-receipt-tracker` repository
5. Railway will auto-detect it's a Python app
6. Add environment variable: `SECRET_KEY` with a secure random string
7. Deploy!

**Tesseract**: Railway supports system packages via `nixpacks.toml` or Dockerfile.

### 2. Render (Free Tier Available)

**Steps:**

1. Go to [render.com](https://render.com)
2. Connect your GitHub account
3. Click "New" → "Web Service"
4. Select your repository
5. Configure:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`
6. Add environment variable: `SECRET_KEY`
7. Deploy!

**Note**: Render's free tier may have limitations with Tesseract OCR.

### 3. PythonAnywhere (Best for Tesseract Support)

**Steps:**

1. Create account at [pythonanywhere.com](https://pythonanywhere.com)
2. Upload your code via Git or file manager
3. Create a new web app (Flask)
4. Install requirements: `pip3.10 install --user -r requirements.txt`
5. Configure WSGI file to point to your app
6. Tesseract is pre-installed!

## 🔧 Environment Variables

Set these environment variables on your chosen platform:

- `SECRET_KEY`: A secure random string (required)
- `DEBUG`: Set to `false` for production
- `PORT`: Usually set automatically by the platform

## 📱 Platform-Specific Notes

### Railway

- Supports Tesseract OCR with buildpacks
- Great free tier
- Automatic HTTPS
- Easy custom domains

### Render

- Free tier available (with limitations)
- May need custom buildpack for Tesseract
- Automatic deploys from GitHub

### PythonAnywhere

- Tesseract pre-installed
- Great for Python apps
- Manual deployment process
- Affordable pricing

### Heroku (Not Recommended)

- Tesseract requires custom buildpack
- Ephemeral filesystem (SQLite issues)
- More complex setup needed

## 🔒 Security Notes

1. **Change SECRET_KEY**: Use a strong, random secret key in production
2. **Database**: Consider upgrading to PostgreSQL for production
3. **File Storage**: Consider cloud storage for uploaded files
4. **HTTPS**: Ensure your deployment platform uses HTTPS

## 🧪 Testing Your Deployment

After deployment:

1. Visit your app URL
2. Try uploading a test Costco receipt
3. Check if OCR processing works
4. Verify database functionality

## 🆘 Troubleshooting

### Common Issues:

1. **Tesseract not found**: Choose a platform that supports system packages
2. **Database errors**: Check if SQLite is supported (some platforms prefer PostgreSQL)
3. **Memory issues**: OCR processing is memory-intensive
4. **File upload errors**: Check upload folder permissions

## 🎯 Recommended Next Steps

1. **Try Railway first** - Best balance of features and simplicity
2. **If Railway doesn't work, try PythonAnywhere** - Best Tesseract support
3. **For production**, consider upgrading to PostgreSQL database
4. **Set up monitoring** and error tracking

Happy deploying! 🎉
