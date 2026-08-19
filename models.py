"""Data structures shared by every module."""

from dataclasses import dataclass, asdict, field
from typing import Optional


# ------------------------------------------------------------- 1. A PLACE
@dataclass
class Place:
    place_id: str
    name: str
    address: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    email: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    rating: Optional[float] = None
    reviews: Optional[int] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    distance_km: Optional[float] = None
    maps_url: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)


# ------------------------------------------------- 2. SEARCH PARAMETERS
@dataclass
class SearchConfig:
    keyword: str
    latitude: float
    longitude: float
    radius_km: float
    max_results: int = 200


# --------------------------------------------------- 3. SPEED SETTINGS
@dataclass
class RateSettings:
    delay_min: float
    delay_max: float
    pause_every: int
    pause_min: float
    pause_max: float


# ------------------------------------------- 4. RUNTIME SHARED COUNTERS
@dataclass
class RunStats:
    found: int = 0
    saved: int = 0
    skipped_out_of_radius: int = 0
    errors: list = field(default_factory=list)
