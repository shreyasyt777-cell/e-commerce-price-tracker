
# Local Development Setup Guide

## Prerequisites
1. Install XAMPP (https://www.apachefriends.org/)
2. Python 3.8+ installed
3. Gmail account with App Password

## Step 1: Install Python Dependencies

```bash
pip install flask flask-sqlalchemy flask-login email-validator apscheduler requests beautifulsoup4 playwright pymysql
```

## Step 2: Setup XAMPP MySQL

1. Start XAMPP Control Panel
2. Start Apache and MySQL services
3. Run the database setup script:

```bash
python setup_mysql.py
```

## Step 3: Configure Email (Gmail)

1. Go to Google Account: https://myaccount.google.com/apppasswords
2. Generate an App Password
3. Note down the 16-character password

## Step 4: Set Environment Variables

### Windows (Command Prompt):
```cmd
set MYSQL_LOCAL=true
set SMTP_USERNAME=your-email@gmail.com
set SMTP_PASSWORD=your-16-char-app-password
```

### Windows (PowerShell):
```powershell
$env:MYSQL_LOCAL="true"
$env:SMTP_USERNAME="your-email@gmail.com"
$env:SMTP_PASSWORD="your-16-char-app-password"
```

### Linux/Mac:
```bash
export MYSQL_LOCAL=true
export SMTP_USERNAME=your-email@gmail.com
export SMTP_PASSWORD=your-16-char-app-password
```

## Step 5: Run the Application

```bash
python app.py
```

The application will be available at: http://localhost:5000

## Configuration Files

- `config_local.py` - Edit this file with your settings (not committed to git)
- `setup_mysql.py` - Run this to create the MySQL database

## Database Selection

The app automatically selects the database:
- **Replit**: Uses PostgreSQL (DATABASE_URL environment variable)
- **Local with MYSQL_LOCAL=true**: Uses XAMPP MySQL
- **Local without MYSQL_LOCAL**: Uses SQLite (pricetracker.db file)

## Troubleshooting

### MySQL Connection Error
- Make sure XAMPP MySQL is running
- Check username/password in environment variables
- Verify database name is 'pricetracker'

### Email Not Sending
- Make sure you're using an App Password, not your regular Gmail password
- Enable "Less secure app access" is NOT needed for App Passwords
- Check SMTP settings are correct

### Product Images Not Showing
- Images are loaded from Amazon/Flipkart URLs
- Make sure the scraper successfully fetched the image URL
- Check browser console for CORS or network errors
