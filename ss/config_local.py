
"""
Local Configuration File
Copy this to config_local.py and update with your settings.
This file should NOT be committed to version control (already in .gitignore)
"""

# Database Configuration for Local Development (XAMPP MySQL)
MYSQL_LOCAL = True  # Set to False to use SQLite or PostgreSQL
MYSQL_USER = 'root'
MYSQL_PASSWORD = ''  # XAMPP default has no password, change if you set one
MYSQL_HOST = 'localhost'
MYSQL_PORT = '3306'
MYSQL_DATABASE = 'pricetracker'

# Email Configuration
# For Gmail, use an App Password (not your regular password)
# Generate one at: https://myaccount.google.com/apppasswords
SMTP_SERVER = 'smtp.gmail.com'
SMTP_PORT = 587
SMTP_USERNAME = 'your-email@gmail.com'  # Replace with your email
SMTP_PASSWORD = 'your-app-password-here'  # Replace with your Gmail app password
FROM_EMAIL = 'your-email@gmail.com'  # Same as SMTP_USERNAME

# To use these settings, set them as environment variables before running:
# For Windows (PowerShell):
# $env:MYSQL_LOCAL="true"
# $env:SMTP_USERNAME="your-email@gmail.com"
# $env:SMTP_PASSWORD="your-app-password"

# For Windows (CMD):
# set MYSQL_LOCAL=true
# set SMTP_USERNAME=your-email@gmail.com
# set SMTP_PASSWORD=your-app-password

# For Linux/Mac:
# export MYSQL_LOCAL=true
# export SMTP_USERNAME=your-email@gmail.com
# export SMTP_PASSWORD=your-app-password
