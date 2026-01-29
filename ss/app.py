import os
import atexit
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from email_validator import validate_email, EmailNotValidError
from apscheduler.schedulers.background import BackgroundScheduler
from models import db, User, TrackedProduct, PriceHistory, PriceAlert
from scraper import ProductScraper, generate_mock_price_history
from email_service import EmailService

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SESSION_SECRET', 'dev-secret-key-change-in-production')

# Database configuration
# For local development with XAMPP MySQL, set MYSQL_LOCAL=true in environment
use_mysql_local = os.environ.get('MYSQL_LOCAL', 'false').lower() == 'true'

if use_mysql_local:
    # XAMPP MySQL configuration for local development
    mysql_user = os.environ.get('MYSQL_USER', 'root')
    mysql_password = os.environ.get('MYSQL_PASSWORD', '')  # XAMPP default has no password
    mysql_host = os.environ.get('MYSQL_HOST', 'localhost')
    mysql_port = os.environ.get('MYSQL_PORT', '3306')
    mysql_database = os.environ.get('MYSQL_DATABASE', 'pricetracker')
    
    database_url = f'mysql+pymysql://{mysql_user}:{mysql_password}@{mysql_host}:{mysql_port}/{mysql_database}'
    print(f"Using MySQL database: {mysql_database}")
else:
    # Use DATABASE_URL from environment (Replit/PostgreSQL) or SQLite as fallback
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        database_url = 'sqlite:///pricetracker.db'
        print("Using SQLite database")
    else:
        print("Using PostgreSQL database from DATABASE_URL")

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_pre_ping': True,
    'pool_recycle': 300,
}

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'

scraper = ProductScraper()
email_service = EmailService()

def check_price_alerts():
    with app.app_context():
        try:
            active_alerts = PriceAlert.query.filter_by(is_active=True).all()
            
            for alert in active_alerts:
                product = TrackedProduct.query.get(alert.product_id)
                if not product:
                    continue
                
                user = User.query.get(alert.user_id)
                if not user:
                    continue
                
                current_price = None
                product_url = None
                
                if alert.platform == 'amazon' and product.amazon_price:
                    current_price = product.amazon_price
                    product_url = product.amazon_url
                elif alert.platform == 'flipkart' and product.flipkart_price:
                    current_price = product.flipkart_price
                    product_url = product.flipkart_url
                elif alert.platform == 'both':
                    if product.amazon_price and product.amazon_price <= alert.target_price:
                        current_price = product.amazon_price
                        product_url = product.amazon_url
                    elif product.flipkart_price and product.flipkart_price <= alert.target_price:
                        current_price = product.flipkart_price
                        product_url = product.flipkart_url
                
                if current_price and current_price <= alert.target_price:
                    email_service.send_price_drop_notification(
                        user.email,
                        product.product_name,
                        current_price,
                        alert.target_price,
                        alert.platform if alert.platform != 'both' else ('amazon' if product_url and 'amazon' in product_url else 'flipkart'),
                        product_url or '',
                        product.product_image
                    )
                    
                    alert.is_active = False
                    alert.triggered_at = datetime.utcnow()
                    db.session.commit()
                    print(f"Alert triggered for product {product.id}, user {user.email}")
                    
        except Exception as e:
            print(f"Error checking price alerts: {e}")

def refresh_all_product_prices():
    with app.app_context():
        try:
            products = TrackedProduct.query.all()
            
            for product in products:
                updated = False
                
                if product.amazon_url:
                    try:
                        amazon_result = scraper.scrape_amazon(product.amazon_url)
                        if amazon_result.get('success'):
                            product.amazon_price = amazon_result['price']
                            product.amazon_original_price = amazon_result.get('original_price')
                            updated = True
                    except Exception as e:
                        print(f"Error scraping Amazon for product {product.id}: {e}")
                
                if product.flipkart_url:
                    try:
                        flipkart_result = scraper.scrape_flipkart(product.flipkart_url)
                        if flipkart_result.get('success'):
                            product.flipkart_price = flipkart_result['price']
                            product.flipkart_original_price = flipkart_result.get('original_price')
                            updated = True
                    except Exception as e:
                        print(f"Error scraping Flipkart for product {product.id}: {e}")
                
                if updated:
                    product.updated_at = datetime.utcnow()
                    
                    history = PriceHistory(
                        product_id=product.id,
                        amazon_price=product.amazon_price,
                        flipkart_price=product.flipkart_price
                    )
                    db.session.add(history)
                    db.session.commit()
                    print(f"Updated prices for product {product.id}")
            
            check_price_alerts()
            
        except Exception as e:
            print(f"Error refreshing product prices: {e}")

scheduler = BackgroundScheduler()
scheduler.add_job(func=refresh_all_product_prices, trigger="interval", hours=6)

# Ensure the scheduler is only started once, even when Flask's debug reloader
# spawns a second process. Without this guard, the job can be registered and
# executed multiple times in parallel, causing inconsistent behaviour.
if not app.debug or os.environ.get("WERKZEUG_RUN_MAIN") == "true":
    scheduler.start()
    # Don't block on shutdown; this avoids hangs when the process exits.
    atexit.register(lambda: scheduler.shutdown(wait=False))

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.after_request
def add_cache_control(response):
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        errors = []
        
        if not username or len(username) < 3:
            errors.append('Username must be at least 3 characters.')
        
        try:
            validate_email(email)
        except EmailNotValidError:
            errors.append('Please enter a valid email address.')
        
        if len(password) < 6:
            errors.append('Password must be at least 6 characters.')
        
        if password != confirm_password:
            errors.append('Passwords do not match.')
        
        if User.query.filter_by(username=username).first():
            errors.append('Username already exists.')
        
        if User.query.filter_by(email=email).first():
            errors.append('Email already registered.')
        
        if errors:
            for error in errors:
                flash(error, 'danger')
            return render_template('register.html')
        
        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        remember = request.form.get('remember', False)
        
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password):
            login_user(user, remember=remember)
            next_page = request.args.get('next')
            flash('Welcome back!', 'success')
            return redirect(next_page if next_page else url_for('dashboard'))
        
        flash('Invalid email or password.', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    products = TrackedProduct.query.filter_by(user_id=current_user.id).order_by(TrackedProduct.created_at.desc()).all()
    return render_template('dashboard.html', products=products)

@app.route('/track-product', methods=['GET', 'POST'])
@login_required
def track_product():
    if request.method == 'POST':
        url = request.form.get('product_url', '').strip()
        
        if not url:
            flash('Please enter a product URL.', 'danger')
            return render_template('track_product.html')
        
        platform = scraper.identify_platform(url)
        if not platform:
            flash('Please enter a valid Amazon or Flipkart product URL.', 'danger')
            return render_template('track_product.html')
        
        result, platform = scraper.scrape_product(url)
        
        if not result or not result.get('success'):
            flash('Could not fetch product details. Please check the URL and try again.', 'danger')
            return render_template('track_product.html')
        
        product = TrackedProduct(
            user_id=current_user.id,
            product_name=result['name'],
            product_image=result.get('image')
        )
        
        if platform == 'amazon':
            product.amazon_url = url
            product.amazon_price = result['price']
            product.amazon_original_price = result.get('original_price')
            
            flipkart_result = scraper.search_flipkart_for_product(result['name'])
            if flipkart_result and flipkart_result.get('success'):
                product.flipkart_url = flipkart_result['url']
                product.flipkart_price = flipkart_result['price']
                product.flipkart_original_price = flipkart_result.get('original_price')
                if not product.product_image and flipkart_result.get('image'):
                    product.product_image = flipkart_result['image']
        else:
            product.flipkart_url = url
            product.flipkart_price = result['price']
            product.flipkart_original_price = result.get('original_price')
            
            amazon_result = scraper.search_amazon_for_product(result['name'])
            if amazon_result and amazon_result.get('success'):
                product.amazon_url = amazon_result['url']
                product.amazon_price = amazon_result['price']
                product.amazon_original_price = amazon_result.get('original_price')
                if not product.product_image and amazon_result.get('image'):
                    product.product_image = amazon_result['image']
        
        db.session.add(product)
        db.session.commit()
        
        initial_history = PriceHistory(
            product_id=product.id,
            amazon_price=product.amazon_price,
            flipkart_price=product.flipkart_price
        )
        db.session.add(initial_history)
        db.session.commit()
        
        flash('Product added successfully!', 'success')
        return redirect(url_for('product_detail', product_id=product.id))
    
    return render_template('track_product.html')

@app.route('/search-products', methods=['GET', 'POST'])
@login_required
def search_products():
    query = ''
    amazon_results = []
    flipkart_results = []
    
    if request.method == 'POST':
        query = request.form.get('query', '').strip()
        if not query:
            flash('Please enter a product name.', 'danger')
        else:
            # Fetch more results from both platforms for a richer comparison view
            amazon_results = scraper.search_amazon_products(query, max_results=20)
            flipkart_results = scraper.search_flipkart_products(query, max_results=20)
            
            if not amazon_results and not flipkart_results:
                flash('No products found. Try a different product name.', 'warning')
    
    return render_template(
        'search_products.html',
        query=query,
        amazon_results=amazon_results,
        flipkart_results=flipkart_results
    )

@app.route('/product/<int:product_id>')
@login_required
def product_detail(product_id):
    product = TrackedProduct.query.filter_by(id=product_id, user_id=current_user.id).first_or_404()
    alerts = PriceAlert.query.filter_by(product_id=product_id, user_id=current_user.id, is_active=True).all()
    return render_template('product_detail.html', product=product, alerts=alerts)

@app.route('/api/price-history/<int:product_id>')
@login_required
def get_price_history(product_id):
    product = TrackedProduct.query.filter_by(id=product_id, user_id=current_user.id).first_or_404()
    
    history = PriceHistory.query.filter_by(product_id=product_id).order_by(PriceHistory.recorded_at).all()
    
    if len(history) < 10:
        mock_history = generate_mock_price_history(
            product_id, 
            product.amazon_price, 
            product.flipkart_price,
            days=90
        )
        return jsonify(mock_history)
    
    return jsonify([{
        'date': h.recorded_at.strftime('%Y-%m-%d'),
        'amazon_price': h.amazon_price,
        'flipkart_price': h.flipkart_price
    } for h in history])

@app.route('/set-alert', methods=['POST'])
@login_required
def set_alert():
    product_id = request.form.get('product_id', type=int)
    target_price = request.form.get('target_price', type=float)
    platform = request.form.get('platform', 'both')
    
    if not product_id or not target_price:
        flash('Please provide all required fields.', 'danger')
        return redirect(request.referrer or url_for('dashboard'))
    
    product = TrackedProduct.query.filter_by(id=product_id, user_id=current_user.id).first()
    if not product:
        flash('Product not found.', 'danger')
        return redirect(url_for('dashboard'))
    
    existing_alert = PriceAlert.query.filter_by(
        product_id=product_id, 
        user_id=current_user.id, 
        platform=platform,
        is_active=True
    ).first()
    
    if existing_alert:
        existing_alert.target_price = target_price
        db.session.commit()
        flash('Price alert updated!', 'success')
    else:
        alert = PriceAlert(
            user_id=current_user.id,
            product_id=product_id,
            target_price=target_price,
            platform=platform
        )
        db.session.add(alert)
        db.session.commit()
        flash('Price alert set successfully!', 'success')
    
    email_service.send_price_alert_confirmation(
        current_user.email,
        product.product_name,
        target_price,
        platform,
        product.product_image
    )
    
    return redirect(url_for('product_detail', product_id=product_id))

@app.route('/delete-alert/<int:alert_id>', methods=['POST'])
@login_required
def delete_alert(alert_id):
    alert = PriceAlert.query.filter_by(id=alert_id, user_id=current_user.id).first()
    if alert:
        product_id = alert.product_id
        db.session.delete(alert)
        db.session.commit()
        flash('Alert deleted.', 'success')
        return redirect(url_for('product_detail', product_id=product_id))
    
    flash('Alert not found.', 'danger')
    return redirect(url_for('dashboard'))

@app.route('/delete-product/<int:product_id>', methods=['POST'])
@login_required
def delete_product(product_id):
    product = TrackedProduct.query.filter_by(id=product_id, user_id=current_user.id).first()
    if product:
        db.session.delete(product)
        db.session.commit()
        flash('Product removed from tracking.', 'success')
    else:
        flash('Product not found.', 'danger')
    
    return redirect(url_for('dashboard'))

@app.route('/refresh-prices/<int:product_id>', methods=['POST'])
@login_required
def refresh_prices(product_id):
    product = TrackedProduct.query.filter_by(id=product_id, user_id=current_user.id).first()
    if not product:
        return jsonify({'error': 'Product not found'}), 404
    
    updated = False
    
    if product.amazon_url:
        amazon_result = scraper.scrape_amazon(product.amazon_url)
        if amazon_result.get('success'):
            product.amazon_price = amazon_result['price']
            product.amazon_original_price = amazon_result.get('original_price')
            updated = True
    
    if product.flipkart_url:
        flipkart_result = scraper.scrape_flipkart(product.flipkart_url)
        if flipkart_result.get('success'):
            product.flipkart_price = flipkart_result['price']
            product.flipkart_original_price = flipkart_result.get('original_price')
            updated = True
    
    if updated:
        product.updated_at = datetime.utcnow()
        
        history = PriceHistory(
            product_id=product.id,
            amazon_price=product.amazon_price,
            flipkart_price=product.flipkart_price
        )
        db.session.add(history)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'amazon_price': product.amazon_price,
            'flipkart_price': product.flipkart_price
        })
    
    return jsonify({'error': 'Could not refresh prices'}), 500

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
