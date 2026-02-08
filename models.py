"""
Data models for Rental Hunter.
"""
import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class Listing:
    """Represents a rental listing from any source."""
    address: str
    city: str
    state: str
    zip_code: str
    price: int
    bedrooms: Optional[int]
    bathrooms: Optional[float]
    sqft: Optional[int]
    url: str
    source: str  # 'realtor', 'zillow', 'redfin'
    photo_url: Optional[str] = None

    @property
    def normalized_address(self) -> str:
        """
        Normalize address for deduplication.
        Handles abbreviations, whitespace, case, etc.
        """
        return normalize_address(self.address, self.city, self.state, self.zip_code)

    def format_alert(self) -> str:
        """Format listing as a Telegram message."""
        lines = [
            f"*NEW RENTAL LISTING*",
            f"",
            f"*{self.address}*",
            f"{self.city}, {self.state} {self.zip_code}",
            f"",
            f"*${self.price:,}/month*",
        ]

        details = []
        if self.bedrooms is not None:
            details.append(f"{self.bedrooms} bed")
        if self.bathrooms is not None:
            bath_str = f"{self.bathrooms:.1f}".rstrip('0').rstrip('.')
            details.append(f"{bath_str} bath")
        if self.sqft is not None:
            details.append(f"{self.sqft:,} sqft")

        if details:
            lines.append(" | ".join(details))

        lines.extend([
            f"",
            f"Source: {self.source.title()}",
            f"[View Listing]({self.url})",
        ])

        return "\n".join(lines)


def normalize_address(address: str, city: str, state: str, zip_code: str) -> str:
    """
    Normalize an address for deduplication.

    Handles:
    - Case normalization
    - Common abbreviations (St -> Street, Ave -> Avenue, etc.)
    - Whitespace normalization
    - Unit/apt number variations
    """
    # Combine into full address
    full = f"{address} {city} {state} {zip_code}"

    # Lowercase
    full = full.lower()

    # Normalize whitespace
    full = re.sub(r'\s+', ' ', full).strip()

    # Remove punctuation except hyphens in unit numbers
    full = re.sub(r'[.,#]', '', full)

    # Standardize directional prefixes/suffixes
    directions = {
        r'\bn\b': 'north',
        r'\bs\b': 'south',
        r'\be\b': 'east',
        r'\bw\b': 'west',
        r'\bne\b': 'northeast',
        r'\bnw\b': 'northwest',
        r'\bse\b': 'southeast',
        r'\bsw\b': 'southwest',
    }
    for pattern, replacement in directions.items():
        full = re.sub(pattern, replacement, full)

    # Standardize street type abbreviations
    street_types = {
        r'\bst\b': 'street',
        r'\bstr\b': 'street',
        r'\bave\b': 'avenue',
        r'\bav\b': 'avenue',
        r'\bblvd\b': 'boulevard',
        r'\bdr\b': 'drive',
        r'\brd\b': 'road',
        r'\bln\b': 'lane',
        r'\bct\b': 'court',
        r'\bcir\b': 'circle',
        r'\bpl\b': 'place',
        r'\bpkwy\b': 'parkway',
        r'\bpky\b': 'parkway',
        r'\bhwy\b': 'highway',
        r'\bter\b': 'terrace',
        r'\bterr\b': 'terrace',
        r'\bway\b': 'way',
    }
    for pattern, replacement in street_types.items():
        full = re.sub(pattern, replacement, full)

    # Standardize unit designations
    unit_types = {
        r'\bapt\b': 'unit',
        r'\bapartment\b': 'unit',
        r'\bste\b': 'unit',
        r'\bsuite\b': 'unit',
        r'\bunit\b': 'unit',
        r'\b#': 'unit ',
    }
    for pattern, replacement in unit_types.items():
        full = re.sub(pattern, replacement, full)

    # Final whitespace cleanup
    full = re.sub(r'\s+', ' ', full).strip()

    return full
