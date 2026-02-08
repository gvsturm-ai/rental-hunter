"""
Configuration for Rental Hunter bot.
"""
import os

# Search criteria
LOCATION = "St. Petersburg, FL"
LOCATION_SLUG = "st-petersburg-fl"  # URL-friendly version
STATE_CODE = "FL"
CITY = "St Petersburg"

# Property filters
PROPERTY_TYPE = "house"  # No condos, apartments, townhouses
MIN_SQFT = 1500
MAX_RENT = 7000
SORT_BY = "newest"

# Telegram configuration (use env vars if available, fallback to defaults)
TELEGRAM_BOT_TOKEN = os.environ.get(
    "TELEGRAM_BOT_TOKEN",
    "8232057605:AAFVkzgSvyAGw-cujT9aT8P-CRdy79mxUWE"
)
TELEGRAM_CHAT_ID = os.environ.get(
    "TELEGRAM_CHAT_ID",
    "8490266898"
)

# Polling settings
POLL_INTERVAL_SECONDS = 300  # 5 minutes

# Database
DB_PATH = os.path.join(os.path.dirname(__file__), "listings.db")

# HTTP settings
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)
REQUEST_TIMEOUT = 30
