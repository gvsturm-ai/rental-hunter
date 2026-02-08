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

# Telegram configuration (set via environment variables or GitHub Secrets)
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
# Multiple chat IDs supported - comma-separated in env var
_chat_ids_raw = os.environ.get("TELEGRAM_CHAT_ID", "")
TELEGRAM_CHAT_IDS = [cid.strip() for cid in _chat_ids_raw.split(",") if cid.strip()]

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
