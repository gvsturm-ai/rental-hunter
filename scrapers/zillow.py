"""
Zillow scraper for rental listings.
Uses embedded JSON data from search results page.
"""
import json
import re
import urllib.request
import urllib.parse
import urllib.error
from typing import List, Optional

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import (
    MIN_SQFT, MAX_RENT, USER_AGENT, REQUEST_TIMEOUT
)
from models import Listing


def scrape_zillow() -> List[Listing]:
    """
    Scrape rental listings from Zillow.

    Returns:
        List of Listing objects matching criteria
    """
    listings = []

    # Zillow search URL for St Pete rentals
    # Using their search state encoding for filters
    search_query = {
        "pagination": {},
        "isMapVisible": False,
        "filterState": {
            "isForRent": {"value": True},
            "isForSaleByAgent": {"value": False},
            "isForSaleByOwner": {"value": False},
            "isNewConstruction": {"value": False},
            "isComingSoon": {"value": False},
            "isAuction": {"value": False},
            "isForSaleForeclosure": {"value": False},
            "isAllHomes": {"value": True},
            "monthlyPayment": {"max": MAX_RENT},
            "sqft": {"min": MIN_SQFT},
            "isApartmentOrCondo": {"value": False},
            "isTownhouse": {"value": False},
            "isManufactured": {"value": False},
            "isApartment": {"value": False},
            "isCondo": {"value": False},
        },
        "isListVisible": True,
    }

    encoded_query = urllib.parse.quote(json.dumps(search_query))
    url = f"https://www.zillow.com/st-petersburg-fl/rentals/?searchQueryState={encoded_query}"

    print(f"[Zillow] Fetching listings...")

    try:
        html = _fetch_page(url)
        if not html:
            print("[Zillow] Failed to fetch page")
            return listings

        # Try to extract listing data from various embedded JSON sources
        data = _extract_listing_data(html)
        if data:
            listings = _parse_listings(data)
            print(f"[Zillow] Found {len(listings)} listings")
        else:
            # Try HTML fallback
            listings = _parse_html_fallback(html)
            print(f"[Zillow] Found {len(listings)} listings via HTML fallback")

    except Exception as e:
        print(f"[Zillow] Error: {e}")

    return listings


def _fetch_page(url: str) -> Optional[str]:
    """Fetch a page and return its HTML content."""
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }

    request = urllib.request.Request(url, headers=headers)

    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT) as response:
            # Handle gzip encoding
            if response.info().get('Content-Encoding') == 'gzip':
                import gzip
                return gzip.decompress(response.read()).decode("utf-8", errors="replace")
            return response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        print(f"[Zillow] HTTP error {e.code}")
        return None
    except urllib.error.URLError as e:
        print(f"[Zillow] URL error: {e.reason}")
        return None
    except Exception as e:
        print(f"[Zillow] Fetch error: {e}")
        return None


def _extract_listing_data(html: str) -> Optional[List[dict]]:
    """Extract listing data from embedded JSON in the page."""

    # Method 1: Look for __NEXT_DATA__ (Next.js apps)
    next_data_pattern = r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>'
    match = re.search(next_data_pattern, html, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group(1))
            results = _extract_from_next_data(data)
            if results:
                return results
        except json.JSONDecodeError:
            pass

    # Method 2: Look for inline JSON with listing data
    # Zillow often embeds data in script tags
    patterns = [
        r'"listResults"\s*:\s*(\[.*?\])\s*,\s*"',
        r'"searchResults"\s*:\s*\{\s*"listResults"\s*:\s*(\[.*?\])',
        r'"cat1"\s*:\s*\{\s*"searchResults"\s*:\s*\{\s*"listResults"\s*:\s*(\[.*?\])',
    ]

    for pattern in patterns:
        match = re.search(pattern, html, re.DOTALL)
        if match:
            try:
                # This might be truncated, try to parse what we can
                json_str = match.group(1)
                # Find the proper end of the array
                data = json.loads(json_str)
                if isinstance(data, list) and len(data) > 0:
                    return data
            except json.JSONDecodeError:
                continue

    # Method 3: Look for gdpClientCache or similar
    cache_pattern = r'"gdpClientCache"\s*:\s*(\{.*?\})\s*,\s*"'
    match = re.search(cache_pattern, html, re.DOTALL)
    if match:
        try:
            cache = json.loads(match.group(1))
            results = []
            for key, value in cache.items():
                if isinstance(value, dict) and "property" in value:
                    results.append(value["property"])
            if results:
                return results
        except json.JSONDecodeError:
            pass

    return None


def _extract_from_next_data(data: dict) -> Optional[List[dict]]:
    """Extract listings from __NEXT_DATA__ structure."""
    try:
        props = data.get("props", {})
        page_props = props.get("pageProps", {})

        # Try different paths
        search_page_state = page_props.get("searchPageState", {})
        cat1 = search_page_state.get("cat1", {})
        search_results = cat1.get("searchResults", {})
        list_results = search_results.get("listResults", [])

        if list_results:
            return list_results

        # Alternative path
        initial_data = page_props.get("initialData", {})
        if "searchResults" in initial_data:
            return initial_data["searchResults"].get("listResults", [])

    except Exception:
        pass

    return None


def _parse_listings(data: List[dict]) -> List[Listing]:
    """Parse listing data into Listing objects."""
    listings = []

    for item in data:
        listing = _parse_single_listing(item)
        if listing:
            listings.append(listing)

    return listings


def _parse_single_listing(item: dict) -> Optional[Listing]:
    """Parse a single listing from Zillow data."""
    try:
        # Get address components
        address = item.get("address", "")
        if not address:
            address_data = item.get("hdpData", {}).get("homeInfo", {})
            street = address_data.get("streetAddress", "")
            city = address_data.get("city", "St Petersburg")
            state = address_data.get("state", "FL")
            zip_code = address_data.get("zipcode", "")
        else:
            # Parse from combined address string
            street = address
            city = "St Petersburg"
            state = "FL"
            zip_code = ""

            # Try to extract city/state/zip
            match = re.match(r'^(.+?),\s*(.+?),\s*([A-Z]{2})\s*(\d{5})?', address)
            if match:
                street = match.group(1)
                city = match.group(2)
                state = match.group(3)
                zip_code = match.group(4) or ""

        if not street:
            return None

        # Get price - handle various formats like "$4,400/mo", "4400", etc.
        price = item.get("unformattedPrice")
        if not price:
            price_raw = item.get("price")
            if isinstance(price_raw, (int, float)):
                price = int(price_raw)
            elif isinstance(price_raw, str):
                # Extract digits from strings like "$4,400/mo"
                match = re.search(r'[\d,]+', price_raw.replace(',', ''))
                if match:
                    price = int(match.group().replace(',', ''))

        if not price:
            return None

        # Get details
        beds = item.get("beds")
        baths = item.get("baths")
        sqft = item.get("area")

        if not sqft:
            sqft = item.get("livingArea")

        # Get URL
        detail_url = item.get("detailUrl", "")
        if detail_url and not detail_url.startswith("http"):
            detail_url = f"https://www.zillow.com{detail_url}"

        zpid = item.get("zpid")
        if not detail_url and zpid:
            detail_url = f"https://www.zillow.com/homedetails/{zpid}_zpid/"

        # Get photo
        photo_url = item.get("imgSrc")
        if not photo_url:
            photos = item.get("carouselPhotos", [])
            if photos:
                photo_url = photos[0].get("url")

        return Listing(
            address=street,
            city=city,
            state=state,
            zip_code=str(zip_code),
            price=int(price),
            bedrooms=int(beds) if beds else None,
            bathrooms=float(baths) if baths else None,
            sqft=int(sqft) if sqft else None,
            url=detail_url,
            source="zillow",
            photo_url=photo_url
        )

    except Exception as e:
        print(f"[Zillow] Parse error: {e}")
        return None


def _parse_html_fallback(html: str) -> List[Listing]:
    """
    Fallback HTML parser when JSON extraction fails.
    """
    listings = []

    # Look for property cards
    card_pattern = r'<article[^>]*data-test="property-card"[^>]*>(.*?)</article>'
    cards = re.findall(card_pattern, html, re.DOTALL)

    for card in cards[:20]:
        try:
            # Extract address
            addr_match = re.search(r'<address[^>]*>([^<]+)</address>', card)
            if not addr_match:
                continue

            address = addr_match.group(1).strip()

            # Extract price
            price_match = re.search(r'\$([0-9,]+)(?:/mo|\/mo)?', card)
            if not price_match:
                continue

            price = int(price_match.group(1).replace(',', ''))

            # Extract URL
            url_match = re.search(r'href="(/homedetails/[^"]+)"', card)
            url = f"https://www.zillow.com{url_match.group(1)}" if url_match else ""

            # Parse address
            parts = address.split(',')
            street = parts[0].strip()
            city = "St Petersburg"
            state = "FL"
            zip_code = ""

            if len(parts) >= 3:
                city = parts[1].strip()
                state_zip = parts[2].strip()
                match = re.match(r'([A-Z]{2})\s*(\d{5})?', state_zip)
                if match:
                    state = match.group(1)
                    zip_code = match.group(2) or ""

            listings.append(Listing(
                address=street,
                city=city,
                state=state,
                zip_code=zip_code,
                price=price,
                bedrooms=None,
                bathrooms=None,
                sqft=None,
                url=url,
                source="zillow",
                photo_url=None
            ))

        except Exception:
            continue

    return listings
