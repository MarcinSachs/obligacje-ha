"""Regex and scraping tests for obligacjeskarbowe.pl and NBP."""
import urllib.request
import re

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "pl-PL,pl;q=0.9,en;q=0.8",
}

# ── Regexes ───────────────────────────────────────────────────────────────────
# Extracts all text from <span class="product-details__list-value"> after "Oprocentowanie:"
RE_OPRO_SPAN = re.compile(
    r"Oprocentowanie:</strong>\s*(?:<br/?\>\s*)?<span[^>]*>\s*(.*?)\s*</span>",
    re.IGNORECASE | re.DOTALL,
)
# Year-1 is provided ONLY if the span starts with a number
RE_YEAR1_IN_SPAN = re.compile(r"^(\d+[,\.]\d+)%")
RE_MARGIN_CPI = re.compile(
    r"mar[zż][aę]\s+(\d+[,\.]\d+)%\s*\+\s*inflacj", re.IGNORECASE)
RE_MARGIN_NBP = re.compile(
    r"referencyjna\s+NBP\s*\+\s*(\d+[,\.]\d+)%", re.IGNORECASE)

SLUGS = {
    "OTS": "obligacje-3-miesieczne-ots",
    "ROR": "obligacje-roczne-ror",
    "DOR": "obligacje-2-letnie-dor",
    "TOS": "obligacje-3-letnie-tos",
    "COI": "obligacje-4-letnie-coi",
    "ROS": "obligacje-6-letnie-ros",
    "EDO": "obligacje-10-letnie-edo",
    "ROD": "obligacje-12-letnie-rod",
}

TEST_SERIES = [
    ("OTS", "ots0726"),   # active
    ("ROR", "ror0427"),   # active
    ("COI", "coi0430"),   # active
    ("COI", "coi0423"),   # historical (2019)
    ("EDO", "edo0436"),   # active
    ("EDO", "edo0130"),   # historical (2020)
    ("ROS", "ros0432"),   # active
    ("ROD", "rod0438"),   # active
]


def fetch(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read().decode("utf-8", errors="replace")


def parse_bond_page(html):
    m_span = RE_OPRO_SPAN.search(html)
    if not m_span:
        return None, None, None, None
    full_text = m_span.group(1).strip()

    # Year-1 only if the span starts with a number
    m_y1 = RE_YEAR1_IN_SPAN.match(full_text)
    year1 = float(m_y1.group(1).replace(",", ".")) / 100.0 if m_y1 else None

    margin = 0.0
    m_cpi = RE_MARGIN_CPI.search(full_text)
    if m_cpi:
        margin = float(m_cpi.group(1).replace(",", ".")) / 100.0
    else:
        m_nbp = RE_MARGIN_NBP.search(full_text)
        if m_nbp:
            margin = float(m_nbp.group(1).replace(",", ".")) / 100.0

    return year1, margin, full_text, m_y1 is not None


print("=" * 60)
print("TEST: obligacjeskarbowe.pl – scraping serii")
print("=" * 60)

for bond_type, series in TEST_SERIES:
    slug = SLUGS[bond_type]
    url = f"https://www.obligacjeskarbowe.pl/oferta-obligacji/{slug}/{series}/"
    try:
        html = fetch(url)
        year1, margin, text, year1_explicit = parse_bond_page(html)
        if text is not None:
            if year1_explicit:
                label = f"rok1={year1*100:.2f}%  marza={margin*100:.2f}%"
            else:
                # no year-1 on the page (historical series after year 1)
                label = f"rok1=N/A (aprox marza={margin*100:.2f}%)"
            print(f"OK   {series.upper():10}  {label}")
            print(f"     Tekst: {text[:100]}")
        else:
            print(f"FAIL {series.upper():10}  brak dopasowania")
            idx = html.lower().find("oprocentowanie")
            print(f"     Fragment (pos={idx}): {html[idx:idx+300]}")
    except Exception as e:
        print(f"FAIL {series.upper():10}  {e}")

print()

# ── NBP regex ──────────────────────────────────────────────────────────────────
print("=" * 60)
print("TEST: NBP – stopa referencyjna regex")
print("=" * 60)
try:
    html_nbp = fetch("https://nbp.pl/podstawowe-stopy-procentowe-archiwum/")

    # Step 1: extract the "interest_rates" section (current rates)
    m_section = re.search(
        r'"interest_rates"\s*:\s*"((?:[^"\\]|\\.)*)"',
        html_nbp,
        re.DOTALL,
    )
    if m_section:
        section = m_section.group(1)
        # Step 2: find id="ref" and its interest rate in this section
        m = re.search(
            r'id=\\"ref\\".*?oprocentowanie=\\"(\d{1,2}[,\.]\d{2})\\"',
            section,
            re.DOTALL,
        )
        if m:
            rate = float(m.group(1).replace(",", "."))
            print(f"OK   interest_rates → id=ref → oprocentowanie: {rate}%")
        else:
            print("FAIL  interest_rates section found, but no id=ref")
            print(f"     Section fragment: {section[:300]}")
    else:
        print("FAIL  no interest_rates section in NBP HTML")
        idx = html_nbp.find('interest_rates')
        print(f"     Fragment (pos={idx}): {html_nbp[max(0, idx-10):idx+200]}")
except Exception as e:
    print(f"FAIL  {e}")
