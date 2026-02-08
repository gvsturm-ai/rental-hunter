# Rental Hunter

Monitors rental listings on Realtor.com, Zillow, and Redfin for houses in St. Petersburg, FL and sends instant Telegram notifications when new listings appear.

## Search Criteria

- **Location**: St. Petersburg, FL
- **Property type**: Houses only (no condos, apartments, townhouses)
- **Minimum sqft**: 1,500
- **Maximum rent**: $7,000/month

## Quick Start

### 1. Test locally

```bash
# Set environment variables
export TELEGRAM_BOT_TOKEN="your_bot_token"
export TELEGRAM_CHAT_ID="your_chat_id"

# Test Telegram notifications
python main.py --test

# Run a single scan
python main.py

# View stats
python main.py --stats
```

### 2. Deploy to GitHub Actions

1. Create a GitHub repo and push this code
2. Go to Settings > Secrets and variables > Actions
3. Add secrets:
   - `TELEGRAM_BOT_TOKEN`: Your Telegram bot token
   - `TELEGRAM_CHAT_ID`: Your Telegram chat ID
4. Go to Actions tab and enable workflows

The bot will run every 5 minutes automatically.

## Commands

| Command | Description |
|---------|-------------|
| `python main.py` | Run a single scan |
| `python main.py --loop` | Run continuously (for local/VPS) |
| `python main.py --test` | Send test notification |
| `python main.py --stats` | Show database statistics |

## Project Structure

```
rental-hunter/
├── main.py              # Entry point
├── config.py            # Configuration settings
├── models.py            # Listing data model
├── db.py                # SQLite for deduplication
├── notify.py            # Telegram notifications
├── scrapers/
│   ├── __init__.py
│   ├── realtor.py       # Realtor.com scraper
│   ├── zillow.py        # Zillow scraper
│   └── redfin.py        # Redfin scraper
└── .github/workflows/
    └── check.yml        # GitHub Actions cron job
```

## How It Works

1. Scrapes listings from all three sources
2. Normalizes addresses for deduplication (handles abbreviations, case, etc.)
3. Checks each listing against SQLite database
4. Sends Telegram notification for new listings
5. Saves to database to prevent duplicate alerts

## Cost

- Python: Free
- GitHub Actions: Free (2,000 min/month)
- Telegram: Free
- SQLite: Free
- **Total: $0/month**
