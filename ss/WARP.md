# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Project overview

This repository contains **PriceTracker**, a Flask-based web application that lets users track products from Amazon India and Flipkart, compare prices across platforms, view recent price history, and receive email alerts when prices drop below a chosen threshold.

The app is designed primarily for local development using SQLite or XAMPP-backed MySQL, with optional PostgreSQL support via `DATABASE_URL` (e.g. Replit environments).

## High-level architecture

### Entry point and web layer

- **`app.py`** is the main entry point and application composition root.
  - Creates the Flask app, configures `SECRET_KEY`, SQLAlchemy, and Flask-Login.
  - Chooses the database connection string based on environment variables (see "Database configuration").
  - Initializes shared service instances:
    - `db` from `models.py` (SQLAlchemy ORM)
    - `ProductScraper` from `scraper.py` for Amazon/Flipkart scraping and search
    - `EmailService` from `email_service.py` for transactional emails
  - Registers all HTTP routes, which fall into a few categories:
    - **Auth & session**: `/register`, `/login`, `/logout` using `flask_login` (`User` model).
    - **Dashboard & CRUD**:
      - `/` (landing page; redirects to `/dashboard` when authenticated).
      - `/dashboard` shows tracked products for the logged-in user.
      - `/track-product` accepts an Amazon/Flipkart URL, scrapes details, and creates a `TrackedProduct` plus initial `PriceHistory`.
      - `/product/<int:product_id>` shows detailed comparison view, price history chart, and alert configuration.
      - `/delete-product/<int:product_id>` removes a product (and cascaded history/alerts via model config).
    - **Alerts**:
      - `/set-alert` creates or updates a `PriceAlert` for a product and sends a confirmation email.
      - `/delete-alert/<int:alert_id>` removes a specific alert.
    - **APIs for the frontend**:
      - `/api/price-history/<int:product_id>` returns JSON price history for Chart.js.
      - `/refresh-prices/<int:product_id>` triggers a one-off scrape to refresh prices for a single product and append a new `PriceHistory` row.
  - Uses `@app.after_request` to enforce no-cache headers for all responses (important when reasoning about browser behavior).

### Data model and persistence

- **`models.py`** defines the ORM schema using Flask-SQLAlchemy:
  - `db = SQLAlchemy()` is initialized in `app.py` with the chosen URI.
  - `User` (extends `UserMixin`):
    - Auth identity with unique `username` and `email`, password hashed via Werkzeug.
    - Relationships:
      - `products` → `TrackedProduct` (cascade delete-orphan).
      - `alerts` → `PriceAlert` (cascade delete-orphan).
  - `TrackedProduct`:
    - Belongs to a `User` via `user_id`.
    - Stores common attributes (`product_name`, `product_image`).
    - Per-platform fields:
      - Amazon: `amazon_url`, `amazon_price`, `amazon_original_price`.
      - Flipkart: `flipkart_url`, `flipkart_price`, `flipkart_original_price`.
    - Timestamps: `created_at`, `updated_at` (auto-updated).
    - Relationships:
      - `price_history` → `PriceHistory` rows.
      - `alerts` → active/inactive `PriceAlert` rows.
  - `PriceHistory`:
    - Time-series table keyed by `product_id`, with `amazon_price`, `flipkart_price`, and `recorded_at`.
    - Used to back the price history chart.
  - `PriceAlert`:
    - Belongs to a `User` and `TrackedProduct`.
    - Stores `target_price`, `platform` (`'amazon'`, `'flipkart'`, or `'both'`), `is_active`, `created_at`, and `triggered_at`.

- Tables are created at startup via `db.create_all()` inside an `app.app_context()` in `app.py`. There are no explicit Alembic migrations.

### Scraping and external HTTP behavior

- **`scraper.py`** encapsulates all scraping and search logic for Amazon and Flipkart.
  - `ProductScraper` maintains a `requests.Session` and a rotating list of realistic user agents.
  - Common utilities:
    - `normalize_url` to coerce bare domains or `http` URLs into HTTPS URLs.
    - `extract_price` to parse a price-like number from arbitrary text, with sanity checks.
  - **Scraping functions**:
    - `scrape_amazon(url)`:
      - Normalizes URL and sends a GET request with Amazon-like headers.
      - Includes delays and retries to mitigate CAPTCHA/robot checks.
      - Saves the last response HTML to `debug_amazon.html` for troubleshooting.
      - Heuristically extracts product title, current price, original price, and main image from multiple selector patterns and fallbacks.
    - `scrape_flipkart(url)`:
      - Similar strategy for Flipkart, using Flipkart-specific CSS selectors and fallbacks.
    - Both functions return a dict with `name`, `price`, optional `original_price` and `image`, the `url`, and a `success` flag plus optional `error`.
  - **Search helpers**:
    - `search_flipkart_for_product(product_name)` and `search_amazon_for_product(product_name)` generate a search URL, parse the results page for the first likely product link, and then call the corresponding scrape function.
    - Used by `/track-product` to automatically find the product on the *other* platform when the user provides only one URL.
  - **Mock history generation**:
    - `generate_mock_price_history(product_id, amazon_price, flipkart_price, days=90)` synthesizes a 90-day price history with small random variations around the current prices.
    - `/api/price-history/<product_id>` uses this when there are fewer than 10 real `PriceHistory` rows, so the chart is always populated.

### Email notifications

- **`email_service.py`** defines `EmailService` for sending HTML emails via SMTP (Gmail by default).
  - Configuration is sourced from environment variables with safe defaults:
    - `SMTP_SERVER` (default `smtp.gmail.com`)
    - `SMTP_PORT` (default `587`)
    - `SMTP_USERNAME`, `SMTP_PASSWORD`, `FROM_EMAIL`
  - `is_configured()` checks that username and password are set; if not, sending is skipped with a log message.
  - High-level methods:
    - `send_price_alert_confirmation(...)` — called after `/set-alert` to confirm that an alert has been created/updated.
    - `send_price_drop_notification(...)` — called from the background job when a price crosses the alert threshold.
  - Both build styled HTML emails and send via `_send_email`, which uses `smtplib` over TLS.

### Background jobs and price refresh

- `app.py` configures an APScheduler `BackgroundScheduler`:
  - `refresh_all_product_prices` job runs every 6 hours:
    - Iterates over all `TrackedProduct` rows.
    - For each platform URL present, calls `scrape_amazon` / `scrape_flipkart` and updates the stored prices and `updated_at` timestamp.
    - Appends a new `PriceHistory` record for each updated product.
    - Calls `check_price_alerts` at the end to evaluate and fire any alerts.
  - `check_price_alerts`:
    - Scans active `PriceAlert` rows.
    - For each, determines the relevant current price(s) for the requested platform(s).
    - Sends a price drop notification email when `current_price <= target_price`, then deactivates the alert and sets `triggered_at`.
  - Scheduler is started on import-time initialization and shut down via an `atexit` handler.

### Templating and frontend

- HTML pages live under `templates/` and compose a Bootstrap-based UI:
  - `base.html` defines the layout, navigation, footer, and flash messaging; all other templates extend it.
  - `index.html` is the public landing page with marketing sections describing the app.
  - `login.html` and `register.html` provide auth forms.
  - `dashboard.html` lists all tracked products with a quick comparison of Amazon vs. Flipkart prices and quick actions.
  - `track_product.html` hosts the URL submission form and UX around tracking a new product.
  - `product_detail.html` shows a full comparison view, price history chart (using Chart.js via `/api/price-history`), and alert management UI.
- Static assets live under `static/` (e.g. `static/css/style.css`), which defines the dark theme, gradients, and general visual styling.

## Environment and configuration

### Database configuration

Database backend is selected at runtime in `app.py` using environment variables:

1. **Local MySQL via XAMPP** (recommended for richer local dev):
   - Set `MYSQL_LOCAL=true` in the environment **before** starting the app.
   - Optional overrides (otherwise defaults are used):
     - `MYSQL_USER` (default `root`)
     - `MYSQL_PASSWORD` (default empty string, XAMPP default)
     - `MYSQL_HOST` (default `localhost`)
     - `MYSQL_PORT` (default `3306`)
     - `MYSQL_DATABASE` (default `pricetracker`)
   - The SQLAlchemy URI is constructed as:
     - `mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}`

2. **PostgreSQL via `DATABASE_URL`**:
   - If `MYSQL_LOCAL` is not true and `DATABASE_URL` is set, that value is used directly as the SQLAlchemy URI.
   - This is intended for hosted environments like Replit.

3. **SQLite fallback**:
   - If neither `MYSQL_LOCAL` is true nor `DATABASE_URL` is set, the app falls back to:
     - `SQLALCHEMY_DATABASE_URI = 'sqlite:///pricetracker.db'`
   - A `pricetracker.db` file is created in the project directory.

There is a helper script **`setup_mysql.py`** that connects to the XAMPP MySQL server and creates the `pricetracker` database if it does not exist. It does **not** create tables; those are created automatically on first app run via `db.create_all()`.

### Email configuration

- Email delivery is optional but required for alert confirmations and price drop notifications to work.
- Configure via environment variables (Gmail with App Password is assumed in `README_LOCAL_SETUP.md` and `config_local.py`):
  - `SMTP_SERVER` (default `smtp.gmail.com`)
  - `SMTP_PORT` (default `587`)
  - `SMTP_USERNAME` — Gmail address used to send emails.
  - `SMTP_PASSWORD` — Gmail App Password (not regular password).
  - `FROM_EMAIL` (defaults to `SMTP_USERNAME` if unset).

If `SMTP_USERNAME` or `SMTP_PASSWORD` is missing, the app logs a message and skips sending emails instead of failing requests.

### Application settings

- `SESSION_SECRET` — if set, used as Flask `SECRET_KEY`; otherwise `app.py` falls back to a hard-coded dev key. For any deployed environment you should set `SESSION_SECRET`.

### Local config helper file

- **`config_local.py`** documents suggested local settings (MySQL and Gmail) and how to export them as environment variables for different shells.
  - This file is already `.gitignore`d and is not imported by `app.py`; it exists purely as a reference template.

## Running the app locally (from README_LOCAL_SETUP.md)

### Prerequisites

- XAMPP installed (for MySQL + Apache, though Apache is not directly used by this app).
- Python 3.8+.
- Gmail account with an App Password (for email alerts).

### Install Python dependencies

```bash
pip install flask flask-sqlalchemy flask-login email-validator apscheduler requests beautifulsoup4 playwright pymysql
```

> Note: `playwright` is installed but not currently imported/used in the codebase; it may have been added for potential future scraping improvements.

### Set up MySQL (optional but recommended)

1. Start **XAMPP Control Panel**.
2. Start **Apache** and **MySQL** services.
3. Create the `pricetracker` database:

```bash
python setup_mysql.py
```

This script uses the hard-coded defaults `root` / empty password on `localhost:3306` and prints next steps when complete.

### Configure environment variables

The README provides shell-specific examples; conceptually you need to set at least:

- `MYSQL_LOCAL=true` (to enable MySQL instead of SQLite or `DATABASE_URL`).
- `SMTP_USERNAME=your-email@gmail.com`.
- `SMTP_PASSWORD=your-16-char-app-password`.

If you skip `MYSQL_LOCAL`, the app will try `DATABASE_URL` and then fall back to SQLite.

### Run the development server

Start the Flask app from the project root:

```bash
python app.py
```

By default the app runs with:

- Host: `0.0.0.0`
- Port: `5000`
- `debug=True`

The main UI will then be available at:

- `http://localhost:5000`

On first run, `db.create_all()` will create all tables in the selected database.

## Testing and linting

- As of this snapshot, the repository does **not** contain a test suite, test runner configuration, or linting configuration (no `pytest` tests, `unittest` modules, or lint configs are present).
- If you introduce tests or linters, add the corresponding commands (e.g. `pytest`, `flake8`, `black`, etc.) to this section so future Warp instances can use them directly.

## Notes for Warp agents

- **Scraping behavior and external dependencies**:
  - All price data depends on the current HTML structure of Amazon India and Flipkart.
  - `scraper.py` is intentionally defensive and uses many selectors and fallbacks; changes here should be tested manually with real product URLs.
  - When debugging scraper issues, inspect the generated `debug_amazon.html` file (written by `scrape_amazon`) to see the exact HTML Amazon returned.
- **Background job side effects**:
  - Running `app.py` starts the APScheduler background job that periodically scrapes all products and may send emails.
  - For ad-hoc scripts or future tests, consider whether the scheduler should be started; if not, you may want to factor scheduler wiring into a separate function that can be skipped.
- **Database migrations**:
  - Schema changes are currently handled by recreating tables via `db.create_all()`; there is no migration tooling. Be cautious when altering models, especially on non-ephemeral databases.
