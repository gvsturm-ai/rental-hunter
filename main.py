#!/usr/bin/env python3
"""
Rental Hunter - Main entry point.

Orchestrates scraping from multiple sources, deduplication,
and Telegram notifications for new rental listings.
"""
import argparse
import sys
import time
from datetime import datetime
from typing import List

from config import POLL_INTERVAL_SECONDS
from models import Listing
from db import is_new_listing, mark_as_seen, get_stats, get_recent_listings
from notify import send_listing_with_photo, send_test_notification
from scrapers import scrape_realtor, scrape_zillow, scrape_redfin


def run_scan() -> int:
    """
    Run a single scan across all sources.

    Returns:
        Number of new listings found and notified
    """
    print(f"\n{'='*60}")
    print(f"Rental Hunter Scan - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")

    all_listings: List[Listing] = []
    new_count = 0

    # Scrape each source
    scrapers = [
        ("Realtor.com", scrape_realtor),
        ("Zillow", scrape_zillow),
        ("Redfin", scrape_redfin),
    ]

    for name, scraper_func in scrapers:
        try:
            listings = scraper_func()
            print(f"  {name}: {len(listings)} listings")
            all_listings.extend(listings)
        except Exception as e:
            print(f"  {name}: ERROR - {e}")

    print(f"\nTotal listings found: {len(all_listings)}")

    # Process listings (dedupe and notify)
    for listing in all_listings:
        normalized = listing.normalized_address

        if is_new_listing(normalized):
            print(f"\n  NEW: {listing.address} (${listing.price}/mo) [{listing.source}]")

            # Send notification
            if send_listing_with_photo(listing):
                print(f"    -> Notification sent!")
            else:
                print(f"    -> Notification failed")

            # Mark as seen
            mark_as_seen(
                normalized_address=normalized,
                original_address=listing.address,
                price=listing.price,
                source=listing.source,
                url=listing.url
            )
            new_count += 1

    print(f"\n{'='*60}")
    print(f"Scan complete. New listings: {new_count}")
    print(f"{'='*60}\n")

    return new_count


def run_loop():
    """Run continuous scanning loop."""
    print("Starting Rental Hunter in continuous mode...")
    print(f"Polling interval: {POLL_INTERVAL_SECONDS} seconds")
    print("Press Ctrl+C to stop.\n")

    try:
        while True:
            run_scan()
            print(f"Sleeping for {POLL_INTERVAL_SECONDS} seconds...")
            time.sleep(POLL_INTERVAL_SECONDS)
    except KeyboardInterrupt:
        print("\nStopping Rental Hunter.")
        sys.exit(0)


def show_stats():
    """Display database statistics."""
    stats = get_stats()

    print("\n" + "="*40)
    print("Rental Hunter Statistics")
    print("="*40)

    print(f"\nTotal listings seen: {stats['total']}")

    if stats.get('by_source'):
        print("\nBy source:")
        for source, count in stats['by_source'].items():
            print(f"  {source}: {count}")

    recent = get_recent_listings(5)
    if recent:
        print("\nMost recent listings:")
        for listing in recent:
            print(f"  - {listing['original_address']} (${listing['price']}) [{listing['source']}]")
            print(f"    First seen: {listing['first_seen_at']}")

    print()


def test_notifications():
    """Send a test notification to verify Telegram setup."""
    print("Sending test notification to Telegram...")

    if send_test_notification():
        print("Success! Check your Telegram for the test message.")
        return True
    else:
        print("Failed to send test notification.")
        print("Please verify your TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID.")
        return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Rental Hunter - Monitor rental listings and get notified"
    )
    parser.add_argument(
        "--loop",
        action="store_true",
        help="Run in continuous loop mode"
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Send a test notification to verify Telegram"
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Show database statistics"
    )

    args = parser.parse_args()

    if args.test:
        success = test_notifications()
        sys.exit(0 if success else 1)

    if args.stats:
        show_stats()
        sys.exit(0)

    if args.loop:
        run_loop()
    else:
        # Single scan
        new_count = run_scan()
        # Exit with 0 regardless of whether new listings were found
        sys.exit(0)


if __name__ == "__main__":
    main()
