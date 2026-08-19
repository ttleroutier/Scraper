"""Google Maps collection with Playwright.

Selectors are grouped in SELECTORS so they can be fixed quickly
when Google changes its markup.
"""

import random
import re
import threading
import time
from typing import Callable, Optional

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

import config
from geo import haversine_km, zoom_for_radius
from models import Place, RateSettings, RunStats, SearchConfig


# ------------------------------------------------------- 1. SELECTORS
SELECTORS = {
    "consent_buttons": [
        'button[aria-label*="Tout accepter"]',
        'button:has-text("Tout accepter")',
        'button:has-text("Accept all")',
        'form[action*="consent"] button',
    ],
    "feed": 'div[role="feed"]',
    "cards": 'a[href*="/maps/place/"]',
    "end_of_list": 'span:has-text("Vous êtes arrivé à la fin de la liste")',
    "detail_name": "h1.DUwDvf",
    "detail_address": 'button[data-item-id="address"]',
    "detail_phone": 'button[data-item-id^="phone:tel:"]',
    "detail_website": 'a[data-item-id="authority"]',
    "detail_category": "button.DkEaL",
    "detail_rating": 'div.F7nice span[aria-hidden="true"]',
    "detail_reviews": 'div.F7nice span[aria-label*="avis"]',
    "detail_summary": "div.PYvSYb",
}


# ------------------------------------------------- 2. RUN CONTROLLER
class ScrapeController:
    """Shared object between the Streamlit UI and the worker thread."""

    def __init__(self):
        self._stop = threading.Event()
        self._running = threading.Event()
        self._running.set()
        self.status = "idle"
        self.captcha_detected = False
        self.stats = RunStats()

    # --- commands sent from the UI
    def pause(self):
        self._running.clear()
        self.status = "paused"

    def resume(self):
        self.captcha_detected = False
        self._running.set()
        self.status = "running"

    def stop(self):
        self._stop.set()
        self._running.set()
        self.status = "stopping"

    # --- checks used inside the worker
    def should_stop(self) -> bool:
        return self._stop.is_set()

    def wait_if_paused(self):
        while not self._running.is_set() and not self._stop.is_set():
            time.sleep(0.5)


# ---------------------------------------------------- 3. RATE LIMITER
class RateLimiter:
    def __init__(self, settings: RateSettings):
        self.settings = settings
        self.counter = 0

    def wait(self, controller: ScrapeController):
        self.counter += 1
        time.sleep(random.uniform(self.settings.delay_min, self.settings.delay_max))

        if self.settings.pause_every and self.counter % self.settings.pause_every == 0:
            long_pause = random.uniform(self.settings.pause_min, self.settings.pause_max)
            controller.status = f"long pause ({int(long_pause)}s)"
            deadline = time.time() + long_pause
            while time.time() < deadline and not controller.should_stop():
                time.sleep(0.5)
            controller.status = "running"


# -------------------------------------------------- 4. PAGE UTILITIES
def accept_consent(page) -> None:
    for selector in SELECTORS["consent_buttons"]:
        try:
            button = page.locator(selector).first
            if button.is_visible(timeout=2000):
                button.click()
                page.wait_for_timeout(1500)
                return
        except Exception:
            continue


def is_captcha(page) -> bool:
    """Detect Google's 'unusual traffic' interstitial. No bypass is attempted."""
    try:
        url = page.url.lower()
        if "/sorry/" in url or "captcha" in url:
            return True
        body = page.locator("body").inner_text(timeout=3000).lower()
        markers = ["unusual traffic", "trafic inhabituel", "je ne suis pas un robot"]
        return any(marker in body for marker in markers)
    except Exception:
        return False


def handle_captcha(page, controller: ScrapeController) -> None:
    """Pause and let the user solve it in the visible browser window."""
    controller.captcha_detected = True
    controller.pause()
    controller.status = "CAPTCHA - solve it in the browser, then press Resume"
    controller.wait_if_paused()


def coordinates_from_url(url: str):
    match = re.search(r"@(-?\d+\.\d+),(-?\d+\.\d+)", url or "")
    if match:
        return float(match.group(1)), float(match.group(2))
    return None, None


def place_id_from_url(url: str) -> str:
    match = re.search(r"!1s([^!?]+)", url or "")
    if match:
        return match.group(1)
    return (url or "").split("?")[0]


# --------------------------------------------------- 5. LIST SCROLLING
def collect_card_links(page, target: int, controller: ScrapeController) -> list:
    """Scroll the results feed and return the place URLs found."""
    links: list[str] = []
    try:
        page.wait_for_selector(SELECTORS["feed"], timeout=config.NAV_TIMEOUT_MS)
    except PlaywrightTimeout:
        return links

    feed = page.locator(SELECTORS["feed"])
    for _ in range(config.MAX_SCROLL_ROUNDS):
        if controller.should_stop():
            break
        controller.wait_if_paused()

        hrefs = page.locator(SELECTORS["cards"]).evaluate_all(
            "nodes => nodes.map(n => n.href)"
        )
        for href in hrefs:
            if href not in links:
                links.append(href)

        if len(links) >= target:
            break
        if page.locator(SELECTORS["end_of_list"]).count() > 0:
            break

        feed.hover()
        page.mouse.wheel(0, 2500)
        page.wait_for_timeout(random.randint(900, 1800))

    return links[:target]


# ------------------------------------------------- 6. DETAIL EXTRACTION
def _text_or_none(page, selector: str) -> Optional[str]:
    try:
        element = page.locator(selector).first
        if element.count() == 0:
            return None
        return element.inner_text(timeout=2500).strip() or None
    except Exception:
        return None


def _aria_value(page, selector: str, prefix: str) -> Optional[str]:
    try:
        element = page.locator(selector).first
        if element.count() == 0:
            return None
        label = element.get_attribute("aria-label") or ""
        return label.replace(prefix, "").strip() or None
    except Exception:
        return None


def extract_place(page, url: str) -> Optional[Place]:
    try:
        page.wait_for_selector(SELECTORS["detail_name"], timeout=config.NAV_TIMEOUT_MS)
    except PlaywrightTimeout:
        return None

    name = _text_or_none(page, SELECTORS["detail_name"])
    if not name:
        return None

    website = None
    try:
        link = page.locator(SELECTORS["detail_website"]).first
        if link.count() > 0:
            website = link.get_attribute("href")
    except Exception:
        pass

    rating = None
    rating_text = _text_or_none(page, SELECTORS["detail_rating"])
    if rating_text:
        try:
            rating = float(rating_text.replace(",", "."))
        except ValueError:
            rating = None

    reviews = None
    reviews_text = _aria_value(page, SELECTORS["detail_reviews"], "")
    if reviews_text:
        digits = re.sub(r"[^\d]", "", reviews_text)
        reviews = int(digits) if digits else None

    latitude, longitude = coordinates_from_url(page.url)

    return Place(
        place_id=place_id_from_url(page.url or url),
        name=name,
        address=_aria_value(page, SELECTORS["detail_address"], "Adresse:"),
        phone=_aria_value(page, SELECTORS["detail_phone"], "Numéro de téléphone:"),
        website=website,
        description=_text_or_none(page, SELECTORS["detail_summary"]),
        category=_text_or_none(page, SELECTORS["detail_category"]),
        rating=rating,
        reviews=reviews,
        latitude=latitude,
        longitude=longitude,
        maps_url=page.url,
    )


# ------------------------------------------------------- 7. MAIN LOOP
def run_scrape(
    search: SearchConfig,
    rates: RateSettings,
    controller: ScrapeController,
    on_result: Callable[[Place], None],
    already_seen: set | None = None,
) -> None:
    """Blocking. Meant to be started in a background thread."""
    already_seen = already_seen or set()
    limiter = RateLimiter(rates)
    controller.status = "starting browser"

    zoom = zoom_for_radius(search.radius_km)
    search_url = (
        f"https://www.google.com/maps/search/{search.keyword.replace(' ', '+')}"
        f"/@{search.latitude},{search.longitude},{zoom}z?hl=fr"
    )

    with sync_playwright() as playwright:
        context = playwright.chromium.launch_persistent_context(
            user_data_dir=config.BROWSER_PROFILE_DIR,
            headless=config.HEADLESS,
            locale=config.LOCALE,
            timezone_id=config.TIMEZONE,
            viewport=config.VIEWPORT,
        )
        page = context.pages[0] if context.pages else context.new_page()
        page.set_default_timeout(config.NAV_TIMEOUT_MS)

        try:
            controller.status = "running"
            page.goto(search_url, wait_until="domcontentloaded")
            accept_consent(page)
            if is_captcha(page):
                handle_captcha(page, controller)

            links = collect_card_links(page, search.max_results, controller)
            controller.stats.found = len(links)

            for url in links:
                if controller.should_stop():
                    break
                controller.wait_if_paused()

                place_key = place_id_from_url(url)
                if place_key in already_seen:
                    continue

                try:
                    page.goto(url, wait_until="domcontentloaded")
                    if is_captcha(page):
                        handle_captcha(page, controller)
                        page.goto(url, wait_until="domcontentloaded")

                    place = extract_place(page, url)
                    if place is None:
                        continue

                    # --- radius filter + distance to the chosen point
                    if place.latitude and place.longitude:
                        place.distance_km = round(
                            haversine_km(
                                search.latitude, search.longitude,
                                place.latitude, place.longitude,
                            ), 2,
                        )
                        if place.distance_km > search.radius_km:
                            controller.stats.skipped_out_of_radius += 1
                            limiter.wait(controller)
                            continue

                    on_result(place)
                    controller.stats.saved += 1
                    already_seen.add(place.place_id)

                except Exception as error:
                    controller.stats.errors.append(f"{url[:60]} -> {error}")

                limiter.wait(controller)

        finally:
            controller.status = "finished"
            try:
                context.close()
            except Exception:
                pass
