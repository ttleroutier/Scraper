"""Central configuration. Change values here, not in the other modules."""

# ---------------------------------------------------------------- 1. PATHS
DATA_DIR = "data"
DB_PATH = f"{DATA_DIR}/results.sqlite"
BROWSER_PROFILE_DIR = "browser_profile"

# ------------------------------------------------------- 2. RATE LIMITING
DEFAULT_DELAY_MIN = 3.0          # seconds between two places
DEFAULT_DELAY_MAX = 8.0
DEFAULT_PAUSE_EVERY = 30         # places before a long pause
DEFAULT_PAUSE_MIN = 30.0         # long pause duration
DEFAULT_PAUSE_MAX = 90.0

# ------------------------------------------------------------- 3. BROWSER
HEADLESS = False                 # keep False so CAPTCHAs stay visible
LOCALE = "fr-FR"
TIMEZONE = "Europe/Paris"
VIEWPORT = {"width": 1400, "height": 900}
NAV_TIMEOUT_MS = 45_000

# -------------------------------------------------------------- 4. SEARCH
MAX_SCROLL_ROUNDS = 40           # safety limit while scrolling the list
DEFAULT_MAX_RESULTS = 200

# ------------------------------------------------- 5. WEBSITE ENRICHMENT
ENRICH_WEBSITES = True
HTTP_TIMEOUT = 10
CONTACT_PATHS = ["", "/contact", "/contacts", "/nous-contacter", "/mentions-legales"]
USER_AGENT = "MapsLeadFinder/1.0 (+contact: your.email@example.com)"
