"""Constants for the Polskie Obligacje Skarbowe integration."""

DOMAIN = "obligacje"

# Update interval in hours — bond rates are updated at most monthly
DEFAULT_SCAN_INTERVAL = 24

# HTTP request timeout (seconds)
REQUEST_TIMEOUT = 30

# ── Config entry keys ─────────────────────────────────────────────────────────
CONF_SERIES = "series"            # e.g. "EDO0130"
CONF_QUANTITY = "quantity"        # number of bonds (each = 100 PLN nominal)
CONF_PURCHASE_DATE = "purchase_date"  # ISO date string "YYYY-MM-DD" (optional)

# ── Bond types → URL slug on obligacjeskarbowe.pl ────────────────────────────
BOND_TYPE_SLUGS: dict[str, str] = {
    "OTS": "obligacje-3-miesieczne-ots",
    "ROR": "obligacje-roczne-ror",
    "DOR": "obligacje-2-letnie-dor",
    "TOS": "obligacje-3-letnie-tos",
    "TOZ": "obligacje-3-letnie-toz",
    "COI": "obligacje-4-letnie-coi",
    "ROS": "obligacje-6-letnie-ros",
    "EDO": "obligacje-10-letnie-edo",
    "ROD": "obligacje-12-letnie-rod",
}

# Duration of each bond type in full years (OTS = 0 → handled as 3 months)
BOND_DURATION_YEARS: dict[str, int] = {
    "OTS": 0,
    "ROR": 1,
    "DOR": 2,
    "TOS": 3,
    "TOZ": 3,
    "COI": 4,
    "ROS": 6,
    "EDO": 10,
    "ROD": 12,
}

# ── Rate basis ────────────────────────────────────────────────────────────────
RATE_BASIS_FIXED = "fixed"        # OTS: single fixed rate for entire term
RATE_BASIS_NBP_REF = "nbp_ref"   # ROR/DOR/TOS: stopa referencyjna NBP + marża
RATE_BASIS_WIBOR6M = "wibor6m"   # TOZ (historical): WIBOR 6M + marża
# COI/ROS/EDO/ROD: inflacja GUS (marzec) + marża
RATE_BASIS_CPI = "cpi"

BOND_RATE_BASIS: dict[str, str] = {
    "OTS": RATE_BASIS_FIXED,
    "ROR": RATE_BASIS_NBP_REF,
    "DOR": RATE_BASIS_NBP_REF,
    "TOS": RATE_BASIS_NBP_REF,
    "TOZ": RATE_BASIS_WIBOR6M,
    "COI": RATE_BASIS_CPI,
    "ROS": RATE_BASIS_CPI,
    "EDO": RATE_BASIS_CPI,
    "ROD": RATE_BASIS_CPI,
}

# Whether interest is capitalized (compounded) — True = all paid at maturity
BOND_CAPITALIZED: dict[str, bool] = {
    "OTS": False,
    "ROR": False,
    "DOR": False,
    "TOS": False,
    "TOZ": False,
    "COI": False,   # "no" capitalization — paid annually
    "ROS": True,
    "EDO": True,
    "ROD": True,
}

# Period type per bond type
PERIOD_SINGLE = "single"          # OTS: one period for entire term
PERIOD_MONTHLY = "monthly"        # ROR/DOR/TOS
PERIOD_SEMIANNUAL = "semiannual"  # TOZ
PERIOD_ANNUAL = "annual"          # COI/ROS/EDO/ROD

BOND_PERIOD_TYPE: dict[str, str] = {
    "OTS": PERIOD_SINGLE,
    "ROR": PERIOD_MONTHLY,
    "DOR": PERIOD_MONTHLY,
    "TOS": PERIOD_MONTHLY,
    "TOZ": PERIOD_SEMIANNUAL,
    "COI": PERIOD_ANNUAL,
    "ROS": PERIOD_ANNUAL,
    "EDO": PERIOD_ANNUAL,
    "ROD": PERIOD_ANNUAL,
}

# ── URLs ──────────────────────────────────────────────────────────────────────
# Works for both active and historical series (just change the slug + series code)
BOND_PAGE_URL = (
    "https://www.obligacjeskarbowe.pl/oferta-obligacji/{slug}/{series}/"
)

# GUS BDL API — annual CPI all-items for Poland
# Variable 217230 = "ogółem" under subject P2955 (WSKAŹNIKI CEN)
# val=103.5 means 3.5% annual inflation; unit-level=0 means whole Poland
GUS_CPI_URL = (
    "https://bdl.stat.gov.pl/api/v1/data/by-variable/217230"
    "?format=json&unit-level=0&page-size=50"
)

# NBP — current base rates page (embeds XML with reference rate in page JSON)
# The page contains a JSON blob with key "interest_rates" holding XML like:
#   <pozycja id="ref" oprocentowanie="3,75" obowiazuje_od="2026-03-05" />
NBP_REF_RATE_URL = "https://nbp.pl/podstawowe-stopy-procentowe-archiwum/"

REQUEST_HEADERS: dict[str, str] = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "pl-PL,pl;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
}

# ── Sensor keys ───────────────────────────────────────────────────────────────
SENSOR_CURRENT_VALUE = "current_value"        # total current value (PLN)
SENSOR_PURCHASE_VALUE = "purchase_value"      # original investment (PLN)
# profit or loss vs purchase (PLN)
SENSOR_PROFIT_LOSS = "profit_loss"
# current period interest rate (%)
SENSOR_CURRENT_RATE = "current_rate"
# accrued but unpaid interest (PLN)
SENSOR_ACCRUED_INTEREST = "accrued_interest"
SENSOR_MATURITY_DATE = "maturity_date"        # date of maturity
SENSOR_DAYS_TO_MATURITY = "days_to_maturity"  # days until maturity

# ── Early redemption fees (PLN per bond, depends on purchase date) ────────────
# Format: {bond_type: [(cutoff_purchase_date_inclusive_or_None, fee_pln), ...]}
# Ordered: oldest cutoff first; None means "this threshold and beyond"
EARLY_REDEMPTION_FEES: dict[str, list[tuple[str | None, float]]] = {
    # no fee (full principal returned)
    "OTS": [],
    "ROR": [(None, 0.50)],
    "DOR": [(None, 0.70)],
    "TOS": [(None, 0.70)],
    "TOZ": [(None, 1.00)],
    "COI": [("2024-08-31", 0.70), (None, 2.00)],
    "ROS": [(None, 2.00)],
    "EDO": [("2024-08-31", 2.00), (None, 3.00)],
    "ROD": [(None, 2.00)],
}

# Regex for valid series code: TYPE (3 uppercase letters) + MM (01-12) + YY (2 digits)
SERIES_PATTERN = r"^(OTS|ROR|DOR|TOS|TOZ|COI|ROS|EDO|ROD)\d{4}$"
