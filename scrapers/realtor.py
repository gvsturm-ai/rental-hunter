"""
Realtor.com scraper for rental listings.
Parses the __NEXT_DATA__ JSON embedded in the page.
"""
import json
import re
import urllib.request
import urllib.error
from typing import List, Optional

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import (
    LOCATION_SLUG, MIN_SQFT, MAX_RENT, USER_AGENT, REQUEST_TIMEOUT
)
from models import Listing


def scrape_realtor() -> List[Listing]:
    """
    Scrape rental listings from Realtor.com.

    Returns:
        List of Listing objects matching criteria
    """
    listings = []

    # Build the search URL
    # Realtor.com URL format for rentals in St Pete, houses only
    url = (
        f"https://www.realtor.com/apartments/{LOCATION_SLUG}"
        f"/type-single-family-home"
        f"/price-na-{MAX_RENT}"
        f"/sqft-{MIN_SQFT}-na"
    )

    print(f"[Realtor] Fetching: {url}")

    try:
        html = _fetch_page(url)
        if not html:
            print("[Realtor] Failed to fetch page")
            return listings

        # Try to extract __NEXT_DATA__ JSON
        data = _extract_next_data(html)
        if data:
            listings = _parse_next_data(data)
            print(f"[Realtor] Found {len(listings)} listings via __NEXT_DATA__")
        else:
            # Fallback: try to parse HTML directly
            listings = _parse_html_fallback(html)
            print(f"[Realtor] Found {len(listings)} listings via HTML fallback")

    except Exception as e:
        print(f"[Realtor] Error: {e}")

    return listings


def _fetch_page(url: str) -> Optional[str]:
    """Fetch a page and return its HTML content."""
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }

    request = urllib.request.Request(url, headers=headers)

    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT) as response:
            return response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        print(f"[Realtor] HTTP error {e.code}")
        return None
    except urllib.error.URLError as e:
        print(f"[Realtor] URL error: {e.reason}")
        return None
    except Exception as e:
        print(f"[Realtor] Fetch error: {e}")
        return None


def _extract_next_data(html: str) -> Optional[dict]:
    """Extract the __NEXT_DATA__ JSON from the page."""
    pattern = r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>'
    match = re.search(pattern, html, re.DOTALL)

    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError as e:
            print(f"[Realtor] JSON parse error: {e}")
            return None
    return None


def _parse_next_data(data: dict) -> List[Listing]:
    """Parse listings from __NEXT_DATA__ structure."""
    listings = []

    try:
        # Navigate to the listings in the data structure
        # This path may change if Realtor.com updates their structure
        props = data.get("props", {})
        page_props = props.get("pageProps", {})

        # Try different possible paths for listings
        search_results = None

        # Path 1: pageProps.properties
        if "properties" in page_props:
            search_results = page_props["properties"]

        # Path 2: pageProps.searchResults.home_search.properties
        elif "searchResults" in page_props:
            sr = page_props["searchResults"]
            if "home_search" in sr:
                search_results = sr["home_search"].get("properties", [])
            elif "properties" in sr:
                search_results = sr["properties"]

        # Path 3: pageProps.pageData.searchResults
        elif "pageData" in page_props:
            pd = page_props["pageData"]
            if "searchResults" in pd:
                search_results = pd["searchResults"].get("properties", [])

        if not search_results:
            print("[Realtor] Could not find listings in __NEXT_DATA__")
            return listings

        for prop in search_results:
            listing = _parse_property(prop)
            if listing:
                listings.append(listing)

    except Exception as e:
        print(f"[Realtor] Parse error: {e}")

    return listings


def _parse_property(prop: dict) -> Optional[Listing]:
    """Parse a single property from the API data."""
    try:
        # Extract location info
        location = prop.get("location", {})
        address_data = location.get("address", {})

        street = address_data.get("line", "")
        city = address_data.get("city", "")
        state = address_data.get("state_code", "")
        zip_code = address_data.get("postal_code", "")

        if not street or not city:
            return None

        # Extract listing details
        list_price = prop.get("list_price")
        if not list_price:
            # Try alternate price fields
            list_price = prop.get("price") or prop.get("list_price_min")

        if not list_price:
            return None

        # Extract property details
        description = prop.get("description", {})
        beds = description.get("beds")
        baths = description.get("baths")
        sqft = description.get("sqft")

        # Build URL
        property_id = prop.get("property_id", "")
        permalink = prop.get("permalink", "")

        if permalink:
            url = f"https://www.realtor.com/realestateandhomes-detail/{permalink}"
        elif property_id:
            url = f"https://www.realtor.com/realestateandhomes-detail/{property_id}"
        else:
            # Construct from address
            slug = f"{street}-{city}-{state}-{zip_code}".lower()
            slug = re.sub(r'[^a-z0-9-]', '-', slug)
            slug = re.sub(r'-+', '-', slug)
            url = f"https://www.realtor.com/realestateandhomes-detail/{slug}"

        # Get photo
        photo_url = None
        photos = prop.get("photos", [])
        if photos and len(photos) > 0:
            photo_url = photos[0].get("href")
        if not photo_url:
            primary_photo = prop.get("primary_photo", {})
            photo_url = primary_photo.get("href")

        return Listing(
            address=street,
            city=city,
            state=state,
            zip_code=zip_code,
            price=int(list_price),
            bedrooms=int(beds) if beds else None,
            bathrooms=float(baths) if baths else None,
            sqft=int(sqft) if sqft else None,
            url=url,
            source="realtor",
            photo_url=photo_url
        )

    except Exception as e:
        print(f"[Realtor] Property parse error: {e}")
        return None


def _parse_html_fallback(html: str) -> List[Listing]:
    """
    Fallback HTML parser when __NEXT_DATA__ isn't available.
    This is less reliable but provides some coverage.
    """
    listings = []

    # Look for property cards in the HTML
    # This pattern may need updating if Realtor.com changes their markup
    card_pattern = r'data-testid="property-card"[^>]*>(.*?)</div>\s*</div>\s*</div>'
    cards = re.findall(card_pattern, html, re.DOTALL)

    for card in cards[:20]:  # Limit to first 20
        try:
            # Extract address
            addr_match = re.search(r'data-testid="card-address[^"]*"[^>]*>([^<]+)', card)
            if not addr_match:
                continue

            address_text = addr_match.group(1).strip()

            # Extract price
            price_match = re.search(r'\$([0-9,]+)', card)
            if not price_match:
                continue

            price = int(price_match.group(1).replace(',', ''))

            # Extract URL
            url_match = re.search(r'href="(/realestateandhomes-detail/[^"]+)"', card)
            url = f"https://www.realtor.com{url_match.group(1)}" if url_match else ""

            # Parse address components (basic)
            parts = address_text.split(',')
            street = parts[0].strip() if len(parts) > 0 else address_text
            city = "St Petersburg"
            state = "FL"
            zip_code = ""

            if len(parts) >= 2:
                city_state = parts[-1].strip()
                zip_match = re.search(r'(\d{5})', city_state)
                if zip_match:
                    zip_code = zip_match.group(1)

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
                source="realtor",
                photo_url=None
            ))

        except Exception as e:
            continue

    return listings
