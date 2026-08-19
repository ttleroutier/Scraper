"""Best-effort public email + description from the company website.

robots.txt is respected and only a few pages are requested.
"""

import re
import urllib.robotparser as robotparser
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from config import CONTACT_PATHS, HTTP_TIMEOUT, USER_AGENT

EMAIL_PATTERN = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
IGNORED_EMAIL_PARTS = ("sentry", "example.com", ".png", ".jpg", "wixpress")


# ------------------------------------------------------- 1. ROBOTS.TXT
def _is_allowed(url: str) -> bool:
    try:
        parsed = urlparse(url)
        parser = robotparser.RobotFileParser()
        parser.set_url(f"{parsed.scheme}://{parsed.netloc}/robots.txt")
        parser.read()
        return parser.can_fetch(USER_AGENT, url)
    except Exception:
        return True


# ------------------------------------------------------------ 2. FETCH
def _fetch(url: str):
    if not _is_allowed(url):
        return None
    try:
        response = requests.get(
            url, headers={"User-Agent": USER_AGENT}, timeout=HTTP_TIMEOUT
        )
        if response.status_code == 200 and "text/html" in response.headers.get("Content-Type", ""):
            return response.text
    except Exception:
        return None
    return None


# ----------------------------------------------------------- 3. PARSE
def _extract_emails(html: str) -> list:
    soup = BeautifulSoup(html, "html.parser")
    found = set()

    for anchor in soup.select('a[href^="mailto:"]'):
        address = anchor.get("href", "")[7:].split("?")[0].strip()
        if address:
            found.add(address)

    found.update(EMAIL_PATTERN.findall(soup.get_text(" ")))
    return [
        email for email in found
        if not any(part in email.lower() for part in IGNORED_EMAIL_PARTS)
    ]


def _extract_description(html: str):
    soup = BeautifulSoup(html, "html.parser")
    for selector in [
        {"name": "description"},
        {"property": "og:description"},
    ]:
        tag = soup.find("meta", attrs=selector)
        if tag and tag.get("content"):
            return tag["content"].strip()[:400]
    return None


# ------------------------------------------------------------ 4. ENTRY
def enrich(website: str):
    """Return (email, description)."""
    if not website:
        return None, None

    email, description = None, None
    for path in CONTACT_PATHS:
        html = _fetch(urljoin(website, path))
        if not html:
            continue
        if description is None:
            description = _extract_description(html)
        emails = _extract_emails(html)
        if emails:
            email = sorted(emails, key=len)[0]
            break

    return email, description
