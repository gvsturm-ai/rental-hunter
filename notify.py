"""
Notification sender for Telegram.
"""
import json
import urllib.request
import urllib.parse
import urllib.error
from typing import Optional

from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_IDS, REQUEST_TIMEOUT
from models import Listing


def send_telegram_message(
    text: str,
    parse_mode: str = "Markdown",
    disable_web_page_preview: bool = False
) -> bool:
    """
    Send a message via Telegram bot API to all configured chat IDs.

    Args:
        text: Message text (supports Markdown formatting)
        parse_mode: 'Markdown' or 'HTML'
        disable_web_page_preview: If True, don't show link previews

    Returns:
        True if sent successfully to at least one recipient, False otherwise
    """
    if not TELEGRAM_CHAT_IDS:
        print("No Telegram chat IDs configured")
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    success_count = 0

    for chat_id in TELEGRAM_CHAT_IDS:
        payload = {
            "chat_id": chat_id,
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
                    success_count += 1
                else:
                    print(f"Telegram API error for {chat_id}: {result}")
        except urllib.error.HTTPError as e:
            print(f"Telegram HTTP error {e.code} for {chat_id}: {e.read().decode()}")
        except urllib.error.URLError as e:
            print(f"Telegram URL error for {chat_id}: {e.reason}")
        except Exception as e:
            print(f"Telegram error for {chat_id}: {e}")

    return success_count > 0


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
    Send a photo with caption via Telegram to all configured chat IDs.

    Args:
        photo_url: URL of the photo to send
        caption: Caption text (supports Markdown)
        parse_mode: 'Markdown' or 'HTML'

    Returns:
        True if sent successfully to at least one recipient, False otherwise
    """
    if not TELEGRAM_CHAT_IDS:
        print("No Telegram chat IDs configured")
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    success_count = 0

    for chat_id in TELEGRAM_CHAT_IDS:
        payload = {
            "chat_id": chat_id,
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
                    success_count += 1
                else:
                    print(f"Telegram API error for {chat_id}: {result}")
        except Exception as e:
            print(f"Telegram photo error for {chat_id}: {e}")

    return success_count > 0


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
