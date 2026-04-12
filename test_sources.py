"""
End-to-end source tests for obligacje-ha.
Run: python test_obligacje.py
"""
import urllib.request
import re
import json
import sys

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

OK = "\033[92mOK\033[0m"
FAIL = "\033[91mFAIL\033[0m"


def fetch(url, accept="text/html"):
    req = urllib.request.Request(url, headers={**HEADERS, "Accept": accept})
    with urllib.request.urlopen(req, timeout=15) as r:
        return r.read().decode("utf-8", errors="replace")


# ─────────────────────────────────────────────────────────────────────────────
# TEST 1: NBP – reference rate
# ─────────────────────────────────────────────────────────────────────────────
print("=" * 60)
print("TEST 1: NBP – stopa referencyjna")
print("=" * 60)
try:
    html = fetch("https://nbp.pl/podstawowe-stopy-procentowe-archiwum/")

    # Regex for unicode-escaped JSON blob (\u003C = <, \" = escaped quote)
    m = re.search(
        r'id=\\"ref\\"[^}]{0,300}?oprocentowanie=\\"(\d{1,2}[,\.]\d{2})\\"',
        html,
    )
    if m:
        rate = float(m.group(1).replace(",", "."))
        print(f"{OK}  Stopa referencyjna: {rate}%  (jako decimal: {rate/100:.4f})")
    else:
        # Fallback – may be unescaped
        m2 = re.search(
            r"id=[\"']ref[\"'][^>]{0,300}?oprocentowanie=[\"'](\d{1,2}[,\.]\d{2})",
            html,
        )
        if m2:
            rate = float(m2.group(1).replace(",", "."))
            print(f"{OK}  (fallback) Stopa referencyjna: {rate}%")
        else:
            print(f"{FAIL}  Nie znaleziono stopy referencyjnej")
            # Debug: find fragment around 'ref'
            idx = html.find('"ref"')
            if idx == -1:
                idx = html.find('id=\\"ref\\"')
            print(f"  Fragment wokół 'ref' (pos={idx}):")
            print(f"  {html[max(0, idx-50):idx+200]}")
except Exception as e:
    print(f"{FAIL}  {e}")

# ─────────────────────────────────────────────────────────────────────────────
# TEST 2: GUS BDL – CPI history
# ─────────────────────────────────────────────────────────────────────────────
print()
print("=" * 60)
print("TEST 2: GUS BDL – historia CPI (zmienna 217230)")
print("=" * 60)
try:
    url = (
        "https://bdl.stat.gov.pl/api/v1/data/by-variable/217230"
        "?format=json&unit-level=0&page-size=50"
    )
    raw = fetch(url, accept="application/json")
    data = json.loads(raw)
    values = data["results"][0]["values"]
    cpi_map = {}
    for item in values:
        year = int(item["year"])
        val = item.get("val")
        if val is not None:
            cpi_map[year] = round((float(val) - 100.0) / 100.0, 4)

    print(f"{OK}  Pobrano {len(cpi_map)} rekordów CPI")
    for y in sorted(cpi_map)[-6:]:
        print(f"  {y}: {cpi_map[y]*100:.1f}%")
except Exception as e:
    print(f"{FAIL}  {e}")

# ─────────────────────────────────────────────────────────────────────────────
# TEST 3: obligacjeskarbowe.pl – scraping series (active and historical)
# ─────────────────────────────────────────────────────────────────────────────
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

# Active and historical series per type
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

RE_YEAR1 = re.compile(r"Oprocentowanie[:\s]*(\d+[,\.]\d+)%", re.IGNORECASE)
RE_MARGIN_CPI = re.compile(
    r"mar[żz][aę]\s+(\d+[,\.]\d+)%\s*\+\s*inflacj", re.IGNORECASE)
RE_MARGIN_NBP = re.compile(
    r"referencyjna\s+NBP\s*\+\s*(\d+[,\.]\d+)%", re.IGNORECASE)
RE_MARGIN_NBP_ZERO = re.compile(
    r"referencyjna\s+NBP\s*\+\s*0,00%", re.IGNORECASE)


def parse_bond_page(html, series):
    m1 = RE_YEAR1.search(html)
    year1 = float(m1.group(1).replace(",", ".")) / 100.0 if m1 else None

    margin = 0.0
    m_cpi = RE_MARGIN_CPI.search(html)
    if m_cpi:
        margin = float(m_cpi.group(1).replace(",", ".")) / 100.0
    else:
        m_nbp = RE_MARGIN_NBP.search(html)
        if m_nbp:
            margin = float(m_nbp.group(1).replace(",", ".")) / 100.0

    return year1, margin


print()
print("=" * 60)
print("TEST 3: obligacjeskarbowe.pl – scraping serii")
print("=" * 60)
for bond_type, series in TEST_SERIES:
    slug = SLUGS[bond_type]
    url = f"https://www.obligacjeskarbowe.pl/oferta-obligacji/{slug}/{series}/"
    try:
        html = fetch(url)
        year1, margin = parse_bond_page(html, series)
        if year1 is not None:
            print(
                f"{OK}  {series.upper()}: rok1={year1*100:.2f}%  marża={margin*100:.2f}%")
        else:
            print(f"{FAIL}  {series.upper()}: nie znaleziono oprocentowania rok1")
            # Debug fragment
            idx = html.lower().find("oprocentowanie")
            print(
                f"         Fragment (pos={idx}): {html[max(0, idx-20):idx+150]}")
    except Exception as e:
        print(f"{FAIL}  {series.upper()}: {e}")

print()
print("Gotowe.")
