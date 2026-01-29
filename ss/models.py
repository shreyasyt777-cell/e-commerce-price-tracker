import os
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    products = db.relationship('TrackedProduct', backref='user', lazy=True, cascade='all, delete-orphan')
    alerts = db.relationship('PriceAlert', backref='user', lazy=True, cascade='all, delete-orphan')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class TrackedProduct(db.Model):
    __tablename__ = 'tracked_products'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    product_name = db.Column(db.String(500), nullable=False)
    product_image = db.Column(db.String(1000))
    
    amazon_url = db.Column(db.String(2000))
    amazon_price = db.Column(db.Float)
    amazon_original_price = db.Column(db.Float)
    
    flipkart_url = db.Column(db.String(2000))
    flipkart_price = db.Column(db.Float)
    flipkart_original_price = db.Column(db.Float)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    price_history = db.relationship('PriceHistory', backref='product', lazy=True, cascade='all, delete-orphan')
    alerts = db.relationship('PriceAlert', backref='product', lazy=True, cascade='all, delete-orphan')

class PriceHistory(db.Model):
    __tablename__ = 'price_history'
    
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('tracked_products.id'), nullable=False)
    amazon_price = db.Column(db.Float)
    flipkart_price = db.Column(db.Float)
    recorded_at = db.Column(db.DateTime, default=datetime.utcnow)

class PriceAlert(db.Model):
    __tablename__ = 'price_alerts'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('tracked_products.id'), nullable=False)
    target_price = db.Column(db.Float, nullable=False)
    platform = db.Column(db.String(20), nullable=False)  # 'amazon', 'flipkart', or 'both'
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    triggered_at = db.Column(db.DateTime)
