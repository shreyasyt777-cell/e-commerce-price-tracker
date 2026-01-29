import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

class EmailService:
    def __init__(self):
        # Email configuration - Set your email credentials here or use environment variables
        # For Gmail, you need to use an App Password (not your regular password)
        # Generate one at: https://myaccount.google.com/apppasswords
        
        self.smtp_server = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = int(os.environ.get('SMTP_PORT', 587))
        
        # Replace these with your email credentials or set them in environment variables
        self.smtp_username = os.environ.get('SMTP_USERNAME', 'your-email@gmail.com')  # Replace with your email
        self.smtp_password = os.environ.get('SMTP_PASSWORD', 'your-app-password')  # Replace with your app password
        self.from_email = os.environ.get('FROM_EMAIL', self.smtp_username)
    
    def is_configured(self):
        return bool(self.smtp_username and self.smtp_password)
    
    def send_price_alert_confirmation(self, to_email, product_name, target_price, platform, product_image=None):
        if not self.is_configured():
            print("Email service not configured. Skipping email send.")
            return False
        
        subject = f"Price Alert Set - {product_name[:50]}..."
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 0; background-color: #f5f5f5; }}
                .container {{ max-width: 600px; margin: 0 auto; background-color: #ffffff; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; text-align: center; }}
                .header h1 {{ color: white; margin: 0; font-size: 24px; }}
                .content {{ padding: 30px; }}
                .product-card {{ background-color: #f8f9fa; border-radius: 10px; padding: 20px; margin: 20px 0; }}
                .product-image {{ text-align: center; margin-bottom: 15px; }}
                .product-image img {{ max-width: 150px; border-radius: 8px; }}
                .product-name {{ font-size: 18px; color: #333; font-weight: bold; margin-bottom: 10px; }}
                .alert-details {{ background-color: #e8f5e9; border-left: 4px solid #4caf50; padding: 15px; margin: 20px 0; }}
                .price {{ font-size: 24px; color: #4caf50; font-weight: bold; }}
                .platform {{ display: inline-block; background-color: #667eea; color: white; padding: 5px 15px; border-radius: 20px; font-size: 14px; }}
                .footer {{ background-color: #f8f9fa; padding: 20px; text-align: center; color: #666; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🔔 Price Alert Confirmed!</h1>
                </div>
                <div class="content">
                    <p>Great news! Your price alert has been successfully set.</p>
                    
                    <div class="product-card">
                        {f'<div class="product-image"><img src="{product_image}" alt="Product"></div>' if product_image else ''}
                        <div class="product-name">{product_name}</div>
                        <span class="platform">{platform.upper()}</span>
                    </div>
                    
                    <div class="alert-details">
                        <p><strong>Target Price:</strong></p>
                        <p class="price">₹{target_price:,.2f}</p>
                        <p>We'll notify you when the price drops to or below your target!</p>
                    </div>
                    
                    <p>Keep tracking prices with PriceTracker and never miss a deal!</p>
                </div>
                <div class="footer">
                    <p>© {datetime.now().year} PriceTracker - Your Smart Shopping Companion</p>
                    <p>This is an automated message. Please do not reply.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return self._send_email(to_email, subject, html_content)
    
    def send_price_drop_notification(self, to_email, product_name, current_price, target_price, platform, product_url, product_image=None):
        if not self.is_configured():
            print("Email service not configured. Skipping email send.")
            return False
        
        subject = f"🎉 Price Drop Alert! - {product_name[:40]}..."
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 0; background-color: #f5f5f5; }}
                .container {{ max-width: 600px; margin: 0 auto; background-color: #ffffff; }}
                .header {{ background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); padding: 30px; text-align: center; }}
                .header h1 {{ color: white; margin: 0; font-size: 24px; }}
                .content {{ padding: 30px; }}
                .product-card {{ background-color: #f8f9fa; border-radius: 10px; padding: 20px; margin: 20px 0; }}
                .product-image {{ text-align: center; margin-bottom: 15px; }}
                .product-image img {{ max-width: 150px; border-radius: 8px; }}
                .product-name {{ font-size: 18px; color: #333; font-weight: bold; margin-bottom: 10px; }}
                .price-comparison {{ display: flex; justify-content: space-around; margin: 20px 0; }}
                .price-box {{ text-align: center; padding: 15px; }}
                .current-price {{ font-size: 28px; color: #11998e; font-weight: bold; }}
                .target-price {{ font-size: 18px; color: #666; text-decoration: line-through; }}
                .buy-button {{ display: inline-block; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; text-decoration: none; padding: 15px 40px; border-radius: 30px; font-size: 18px; font-weight: bold; margin: 20px 0; }}
                .platform {{ display: inline-block; background-color: #667eea; color: white; padding: 5px 15px; border-radius: 20px; font-size: 14px; }}
                .footer {{ background-color: #f8f9fa; padding: 20px; text-align: center; color: #666; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🎉 Price Drop Alert!</h1>
                </div>
                <div class="content">
                    <p>The product you're tracking has dropped below your target price!</p>
                    
                    <div class="product-card">
                        {f'<div class="product-image"><img src="{product_image}" alt="Product"></div>' if product_image else ''}
                        <div class="product-name">{product_name}</div>
                        <span class="platform">{platform.upper()}</span>
                    </div>
                    
                    <div class="price-comparison">
                        <div class="price-box">
                            <p>Your Target</p>
                            <p class="target-price">₹{target_price:,.2f}</p>
                        </div>
                        <div class="price-box">
                            <p>Current Price</p>
                            <p class="current-price">₹{current_price:,.2f}</p>
                        </div>
                    </div>
                    
                    <div style="text-align: center;">
                        <a href="{product_url}" class="buy-button">Buy Now on {platform.capitalize()}</a>
                    </div>
                    
                    <p style="color: #666; font-size: 14px;">Hurry! Prices can change at any time.</p>
                </div>
                <div class="footer">
                    <p>© {datetime.now().year} PriceTracker - Your Smart Shopping Companion</p>
                    <p>This is an automated message. Please do not reply.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return self._send_email(to_email, subject, html_content)
    
    def _send_email(self, to_email, subject, html_content):
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.from_email
            msg['To'] = to_email
            
            html_part = MIMEText(html_content, 'html')
            msg.attach(html_part)
            
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.sendmail(self.from_email, to_email, msg.as_string())
            
            print(f"Email sent successfully to {to_email}")
            return True
            
        except Exception as e:
            print(f"Failed to send email: {e}")
            return False
