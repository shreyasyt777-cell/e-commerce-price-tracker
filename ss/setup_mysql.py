
"""
MySQL Database Setup Script for XAMPP
Run this script to create the database in your XAMPP MySQL server
"""
import pymysql
import os

# Configuration (update these if needed)
MYSQL_USER = 'root'
MYSQL_PASSWORD = ''  # XAMPP default
MYSQL_HOST = 'localhost'
MYSQL_PORT = 3306
DATABASE_NAME = 'pricetracker'

def setup_database():
    try:
        # Connect to MySQL server (without database)
        connection = pymysql.connect(
            host=MYSQL_HOST,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            port=MYSQL_PORT
        )
        
        cursor = connection.cursor()
        
        # Create database if it doesn't exist
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DATABASE_NAME} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        print(f"✓ Database '{DATABASE_NAME}' created/verified successfully!")
        
        cursor.close()
        connection.close()
        
        print("\nNext steps:")
        print("1. Set environment variables:")
        print("   set MYSQL_LOCAL=true")
        print("   set SMTP_USERNAME=your-email@gmail.com")
        print("   set SMTP_PASSWORD=your-app-password")
        print("2. Run: python app.py")
        print("\nThe tables will be created automatically on first run.")
        
    except Exception as e:
        print(f"✗ Error setting up database: {e}")
        print("\nMake sure XAMPP MySQL is running!")

if __name__ == "__main__":
    print("Setting up MySQL database for PriceTracker...")
    setup_database()
