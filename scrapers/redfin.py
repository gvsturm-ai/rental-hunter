"""
Redfin scraper for rental listings.
Uses the Redfin stingray GIS API.
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


# St. Petersburg, FL bounding box (approximate)
ST_PETE_BOUNDS = {
    "south": 27.6500,
    "north": 27.8500,
    "west": -82.7800,
    "east": -82.5500,
}

# Redfin region ID for St. Petersburg, FL
ST_PETE_REGION_ID = 17193
ST_PETE_REGION_TYPE = 6  # City


def scrape_redfin() -> List[Listing]:
    """
    Scrape rental listings from Redfin.

    Returns:
        List of Listing objects matching criteria
    """
    listings = []

    print("[Redfin] Fetching listings...")

    try:
        # Try the GIS API first (most reliable)
        listings = _scrape_via_gis_api()
        if listings:
            print(f"[Redfin] Found {len(listings)} listings via GIS API")
            return listings

        # Fallback to search page
        listings = _scrape_via_search_page()
        if listings:
            print(f"[Redfin] Found {len(listings)} listings via search page")
            return listings

        print("[Redfin] No listings found")

    except Exception as e:
        print(f"[Redfin] Error: {e}")

    return listings


def _scrape_via_gis_api() -> List[Listing]:
    """Use Redfin's GIS API to fetch listings."""
    listings = []

    # Build the API URL
    # Redfin's stingray API endpoint
    params = {
        "al": 1,
        "include_nearby_homes": "true",
        "isRentals": "true",
        "num_homes": 100,
        "ord": "days-on-redfin-asc",
        "page_number": 1,
        "region_id": ST_PETE_REGION_ID,
        "region_type": ST_PETE_REGION_TYPE,
        "sf": "1,2,5,6,7",  # Various filters
        "status": 9,  # Active rentals
        "uipt": "1",  # Single family homes
        "v": 8,
    }

    query_string = urllib.parse.urlencode(params)
    url = f"https://www.redfin.com/stingray/api/gis?{query_string}"

    try:
        data = _fetch_api(url)
        if not data:
            return listings

        # Parse the response
        homes = data.get("homes", [])

        for home in homes:
            listing = _parse_home(home)
            if listing:
                # Apply our filters
                if listing.sqft and listing.sqft < MIN_SQFT:
                    continue
                if listing.price > MAX_RENT:
                    continue
                listings.append(listing)

    except Exception as e:
        print(f"[Redfin] GIS API error: {e}")

    return listings


def _fetch_api(url: str) -> Optional[dict]:
    """Fetch from Redfin API and parse response."""
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
        "Accept-Language": "en-US,en;q=0.5",
        "Referer": "https://www.redfin.com/",
    }

    request = urllib.request.Request(url, headers=headers)

    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT) as response:
            content = response.read().decode("utf-8", errors="replace")

            # Redfin API returns data with a prefix like "{}&&" that needs to be stripped
            if content.startswith("{}&&"):
                content = content[4:]

            return json.loads(content)

    except urllib.error.HTTPError as e:
        print(f"[Redfin] HTTP error {e.code}")
        return None
    except urllib.error.URLError as e:
        print(f"[Redfin] URL error: {e.reason}")
        return None
    except json.JSONDecodeError as e:
        print(f"[Redfin] JSON parse error: {e}")
        return None
    except Exception as e:
        print(f"[Redfin] Fetch error: {e}")
        return None


def _parse_home(home: dict) -> Optional[Listing]:
    """Parse a home from Redfin API response."""
    try:
        # Get price
        price_info = home.get("priceInfo", {})
        price = price_info.get("amount")

        if not price:
            # Try alternate field
            price = home.get("price", {}).get("value")

        if not price:
            return None

        # Get address info
        street = home.get("streetLine", {}).get("value", "")
        if not street:
            street = home.get("address", "")

        city = home.get("city", "St Petersburg")
        state = home.get("state", "FL")
        zip_code = home.get("zip", "")

        if not street:
            return None

        # Get property details
        beds = home.get("beds")
        baths = home.get("baths")
        sqft = home.get("sqFt", {}).get("value")

        if not sqft:
            sqft = home.get("sqftInfo", {}).get("amount")

        # Build URL
        url_path = home.get("url", "")
        if url_path:
            url = f"https://www.redfin.com{url_path}"
        else:
            # Construct URL from address
            listing_id = home.get("listingId") or home.get("mlsId", {}).get("value", "")
            if listing_id:
                url = f"https://www.redfin.com/FL/St-Petersburg/{listing_id}"
            else:
                url = "https://www.redfin.com"

        # Get photo
        photo_url = None
        photos = home.get("photos", {})
        if photos:
            photo_url = photos.get("primaryPhotoUrl", {}).get("value")
        if not photo_url:
            photo_url = home.get("primaryPhotoUrl")

        return Listing(
            address=street,
            city=city,
            state=state,
            zip_code=str(zip_code),
            price=int(price),
            bedrooms=int(beds) if beds else None,
            bathrooms=float(baths) if baths else None,
            sqft=int(sqft) if sqft else None,
            url=url,
            source="redfin",
            photo_url=photo_url
        )

    except Exception as e:
        print(f"[Redfin] Parse error: {e}")
        return None


def _scrape_via_search_page() -> List[Listing]:
    """Fallback: scrape the search results page directly."""
    listings = []

    url = (
        "https://www.redfin.com/city/17193/FL/St-Petersburg"
        "/apartments-for-rent"
        "/filter/property-type=house,min-sqft=1500,max-price=7000"
    )

    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }

    request = urllib.request.Request(url, headers=headers)

    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT) as response:
            html = response.read().decode("utf-8", errors="replace")

        # Try to find embedded JSON data
        # Redfin embeds data in script tags
        script_pattern = r'<script[^>]*>window\.__reactServerState\s*=\s*(\{.*?\});</script>'
        match = re.search(script_pattern, html, re.DOTALL)

        if match:
            try:
                data = json.loads(match.group(1))
                homes = _extract_homes_from_state(data)
                for home in homes:
                    listing = _parse_home(home)
                    if listing:
                        if listing.sqft and listing.sqft < MIN_SQFT:
                            continue
                        if listing.price > MAX_RENT:
                            continue
                        listings.append(listing)
            except json.JSONDecodeError:
                pass

        # HTML fallback
        if not listings:
            listings = _parse_html_fallback(html)

    except Exception as e:
        print(f"[Redfin] Search page error: {e}")

    return listings


def _extract_homes_from_state(data: dict) -> List[dict]:
    """Extract homes from Redfin's server state object."""
    homes = []

    try:
        # Navigate the nested structure
        for key, value in data.items():
            if isinstance(value, dict):
                if "homes" in value:
                    homes.extend(value["homes"])
                elif "searchResults" in value:
                    results = value["searchResults"]
                    if isinstance(results, dict) and "homes" in results:
                        homes.extend(results["homes"])
    except Exception:
        pass

    return homes


def _parse_html_fallback(html: str) -> List[Listing]:
    """Parse listings from HTML when API/JSON methods fail."""
    listings = []

    # Look for home cards
    card_pattern = r'<div[^>]*class="[^"]*HomeCard[^"]*"[^>]*>(.*?)</div>\s*</div>\s*</div>'
    cards = re.findall(card_pattern, html, re.DOTALL)

    for card in cards[:20]:
        try:
            # Extract address
            addr_match = re.search(r'class="[^"]*homeAddress[^"]*"[^>]*>([^<]+)', card, re.IGNORECASE)
            if not addr_match:
                continue

            address = addr_match.group(1).strip()

            # Extract price
            price_match = re.search(r'\$([0-9,]+)', card)
            if not price_match:
                continue

            price = int(price_match.group(1).replace(',', ''))

            # Check price filter
            if price > MAX_RENT:
                continue

            # Extract URL
            url_match = re.search(r'href="(/FL/[^"]+)"', card)
            url = f"https://www.redfin.com{url_match.group(1)}" if url_match else ""

            # Parse address (assume St Pete, FL)
            street = address
            city = "St Petersburg"
            state = "FL"
            zip_code = ""

            zip_match = re.search(r'(\d{5})', address)
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
                source="redfin",
                photo_url=None
            ))

        except Exception:
            continue

    return listings
