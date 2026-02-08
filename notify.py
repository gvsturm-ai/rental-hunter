"""
Notification sender for Telegram.
"""
import json
import urllib.request
import urllib.parse
import urllib.error
from typing import Optional

from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, REQUEST_TIMEOUT
from models import Listing


def send_telegram_message(
    text: str,
    parse_mode: str = "Markdown",
    disable_web_page_preview: bool = False
) -> bool:
    """
    Send a message via Telegram bot API.

    Args:
        text: Message text (supports Markdown formatting)
        parse_mode: 'Markdown' or 'HTML'
        disable_web_page_preview: If True, don't show link previews

    Returns:
        True if sent successfully, False otherwise
    """
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": disable_web_page_preview,
    }

    data = json.dumps(payload).encode("utf-8")

    request = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT) as response:
            result = json.loads(response.read().decode("utf-8"))
            if result.get("ok"):
                return True
            else:
                print(f"Telegram API error: {result}")
                return False
    except urllib.error.HTTPError as e:
        print(f"Telegram HTTP error {e.code}: {e.read().decode()}")
        return False
    except urllib.error.URLError as e:
        print(f"Telegram URL error: {e.reason}")
        return False
    except Exception as e:
        print(f"Telegram error: {e}")
        return False


def send_listing_alert(listing: Listing) -> bool:
    """Send a formatted alert for a new listing."""
    message = listing.format_alert()
    return send_telegram_message(message)


def send_photo_with_caption(
    photo_url: str,
    caption: str,
    parse_mode: str = "Markdown"
) -> bool:
    """
    Send a photo with caption via Telegram.

    Args:
        photo_url: URL of the photo to send
        caption: Caption text (supports Markdown)
        parse_mode: 'Markdown' or 'HTML'

    Returns:
        True if sent successfully, False otherwise
    """
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"

    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "photo": photo_url,
        "caption": caption,
        "parse_mode": parse_mode,
    }

    data = json.dumps(payload).encode("utf-8")

    request = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT) as response:
            result = json.loads(response.read().decode("utf-8"))
            if result.get("ok"):
                return True
            else:
                print(f"Telegram API error: {result}")
                return False
    except Exception as e:
        print(f"Telegram photo error: {e}")
        return False


def send_listing_with_photo(listing: Listing) -> bool:
    """
    Send a listing alert with photo if available.
    Falls back to text-only if photo fails.
    """
    if listing.photo_url:
        caption = listing.format_alert()
        if send_photo_with_caption(listing.photo_url, caption):
            return True
        # Fall back to text-only if photo fails
        print(f"Photo send failed, falling back to text for {listing.address}")

    return send_listing_alert(listing)


def send_test_notification() -> bool:
    """Send a test notification to verify Telegram is configured correctly."""
    message = (
        "*Rental Hunter Test*\n\n"
        "If you see this message, Telegram notifications are working correctly!\n\n"
        "The bot will notify you when new rental listings match your criteria:\n"
        "- Location: St. Petersburg, FL\n"
        "- Type: Houses only\n"
        "- Min sqft: 1,500\n"
        "- Max rent: $7,000/month"
    )
    return send_telegram_message(message)
