"""Data coordinator for Polskie Obligacje Skarbowe integration.

Strategy:
  1. Derive bond type from the series code (e.g. "EDO0130" → type "EDO").
  2. Fetch bond page on obligacjeskarbowe.pl/{slug}/{series}/ — works for
     both active and historical series — and parse year-1 rate + margin.
  3. Fetch macro reference data:
       - CPI history from GUS BDL API  (for COI / ROS / EDO / ROD)
       - NBP reference rate             (for ROR / DOR / TOS / TOZ)
  4. Pass all data to calculator.calculate_bond_value().
"""
from __future__ import annotations

import json
import logging
import re
from datetime import date, timedelta
from typing import Any

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .calculator import (
    calculate_bond_value,
    derive_purchase_month_year,
    parse_series,
)
from .const import (
    BOND_PAGE_URL,
    BOND_RATE_BASIS,
    BOND_TYPE_SLUGS,
    CONF_PURCHASE_DATE,
    CONF_QUANTITY,
    CONF_SERIES,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    GUS_CPI_URL,
    NBP_REF_RATE_URL,
    RATE_BASIS_CPI,
    RATE_BASIS_NBP_REF,
    RATE_BASIS_WIBOR6M,
    REQUEST_HEADERS,
    REQUEST_TIMEOUT,
)

_LOGGER = logging.getLogger(__name__)

# ── HTML scraping patterns ────────────────────────────────────────────────────
# Matches the Oprocentowanie value span on obligacjeskarbowe.pl:
#   <strong>Oprocentowanie:</strong><br>
#   <span class="product-details__list-value">4,75%, w skali roku…</span>
_RE_OPRO_SPAN = re.compile(
    r"Oprocentowanie:</strong>\s*(?:<br/?\>\s*)?<span[^>]*>\s*(.*?)\s*</span>",
    re.IGNORECASE | re.DOTALL,
)
# Year-1 rate is explicit only when a percentage leads the span text.
_RE_YEAR1_IN_SPAN = re.compile(r"^(\d+[,\.]\d+)%")
# Matches CPI-based margin: "marża 1,50% + inflacja"
_RE_MARGIN_CPI = re.compile(
    r"marż[aę]\s+(\d+[,\.]\d+)%\s*\+\s*inflacj", re.IGNORECASE
)
# Matches non-zero NBP-based margin: "referencyjna NBP+1,00%"
_RE_MARGIN_NBP = re.compile(
    r"referencyjna\s+NBP\s*\+\s*(\d+[,\.]\d+)%", re.IGNORECASE
)


def _parse_rate(raw: str) -> float:
    """Convert Polish decimal string to a decimal rate (e.g. '1,50' → 0.015)."""
    return float(raw.replace(",", ".")) / 100.0


class ObligacjeCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator for a single bond position (one config entry)."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{entry.data[CONF_SERIES]}",
            update_interval=timedelta(hours=DEFAULT_SCAN_INTERVAL),
        )
        self._entry = entry
        self._series: str = entry.data[CONF_SERIES].upper()
        self._quantity: int = int(entry.data[CONF_QUANTITY])

        purchase_date_str: str | None = entry.data.get(CONF_PURCHASE_DATE)
        if purchase_date_str:
            self._purchase_date = date.fromisoformat(purchase_date_str)
        else:
            # Estimate from series code — default to 1st of the purchase month
            m, y = derive_purchase_month_year(self._series)
            self._purchase_date = date(y, m, 1)

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch bond parameters, macro data, calculate current value."""
        bond_type, _, _ = parse_series(self._series)
        slug = BOND_TYPE_SLUGS.get(bond_type)
        if not slug:
            raise UpdateFailed(
                f"Unknown bond type in series: {self._series!r}")

        url = BOND_PAGE_URL.format(slug=slug, series=self._series.lower())
        rate_basis = BOND_RATE_BASIS[bond_type]

        try:
            async with aiohttp.ClientSession(headers=REQUEST_HEADERS) as session:
                year1_rate, margin = await self._fetch_bond_params(session, url)

                cpi_history: dict[int, float] = {}
                nbp_ref_rate: float = 0.0

                if rate_basis == RATE_BASIS_CPI:
                    cpi_history = await self._fetch_cpi_history(session)
                elif rate_basis in (RATE_BASIS_NBP_REF, RATE_BASIS_WIBOR6M):
                    nbp_ref_rate = await self._fetch_nbp_ref_rate(session)

        except aiohttp.ClientError as exc:
            raise UpdateFailed(f"Network error: {exc}") from exc

        result = calculate_bond_value(
            series=self._series,
            purchase_date=self._purchase_date,
            quantity=self._quantity,
            year1_rate=year1_rate,
            margin=margin,
            cpi_history=cpi_history,
            nbp_ref_rate=nbp_ref_rate,
        )
        # Attach metadata for sensors / device info
        result["series"] = self._series
        result["bond_type"] = bond_type
        result["quantity"] = self._quantity
        result["purchase_date"] = self._purchase_date
        return result

    # ── Private fetch helpers ─────────────────────────────────────────────────

    async def _fetch_bond_params(
        self, session: aiohttp.ClientSession, url: str
    ) -> tuple[float, float]:
        """Scrape year-1 rate and margin from obligacjeskarbowe.pl."""
        async with session.get(
            url, timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
        ) as resp:
            if resp.status == 404:
                raise UpdateFailed(f"Bond series page not found (404): {url}")
            resp.raise_for_status()
            html = await resp.text()

        m_span = _RE_OPRO_SPAN.search(html)
        if not m_span:
            raise UpdateFailed(
                f"Could not find Oprocentowanie span on page: {url}"
            )
        span_text = m_span.group(1)

        # Year-1 rate is only shown when span text starts with a number.
        # For historical bonds past year 1 the page omits it.
        m_y1 = _RE_YEAR1_IN_SPAN.match(span_text)
        year1_explicit: float | None = _parse_rate(
            m_y1.group(1)) if m_y1 else None

        margin = 0.0
        m_cpi = _RE_MARGIN_CPI.search(span_text)
        if m_cpi:
            margin = _parse_rate(m_cpi.group(1))
        else:
            m_nbp = _RE_MARGIN_NBP.search(span_text)
            if m_nbp:
                margin = _parse_rate(m_nbp.group(1))
            # pure-NBP / pure-fixed with no surplus → margin stays 0.0

        if year1_explicit is None:
            _LOGGER.warning(
                "%s: year-1 rate not shown on page (bond past period 1); "
                "using margin=%.4f as approximation",
                self._series,
                margin,
            )
            year1_rate = margin
        else:
            year1_rate = year1_explicit

        _LOGGER.debug(
            "%s scraped: year1_rate=%.4f  margin=%.4f", self._series, year1_rate, margin
        )
        return year1_rate, margin

    async def _fetch_cpi_history(
        self, session: aiohttp.ClientSession
    ) -> dict[int, float]:
        """Fetch annual CPI from GUS BDL API.

        Returns {year: cpi_decimal} where year is the year of the March GUS
        announcement (e.g. 2023 → CPI used for bond periods starting in 2023).
        GUS returns index values — e.g. 105.1 means 5.1 % annual inflation.
        """
        try:
            async with session.get(
                GUS_CPI_URL,
                timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT),
                headers={"Accept": "application/json"},
            ) as resp:
                resp.raise_for_status()
                data = await resp.json(content_type=None)
        except Exception as exc:  # noqa: BLE001
            _LOGGER.warning("Could not fetch GUS CPI data: %s", exc)
            return {}

        cpi_map: dict[int, float] = {}
        try:
            for item in data["results"][0]["values"]:
                year = int(item["year"])
                raw = item.get("val")
                if raw is not None:
                    cpi_map[year] = (float(raw) - 100.0) / 100.0
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            _LOGGER.warning("Unexpected GUS CPI response format: %s", exc)

        _LOGGER.debug("CPI history: %s", cpi_map)
        return cpi_map

    async def _fetch_nbp_ref_rate(
        self, session: aiohttp.ClientSession
    ) -> float:
        """Fetch current NBP monetary policy reference rate.

        Scrapes https://nbp.pl/podstawowe-stopy-procentowe-archiwum/ which
        embeds a JSON blob containing XML with the current rates. The XML
        contains an element like:
            <pozycja id="ref" oprocentowanie="3,75" obowiazuje_od="2026-03-05"/>

        Returns rate as decimal (e.g. 0.0375 for 3.75 %).
        Falls back to 0.0 on any error — caller should handle gracefully.
        """
        try:
            async with session.get(
                NBP_REF_RATE_URL,
                timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT),
            ) as resp:
                resp.raise_for_status()
                html = await resp.text()

            # The page embeds a JSON blob with two XML sections:
            #   "stopy_procentowe_archiwum" – historical rates (may contain old values)
            #   "interest_rates"            – current rates (has the 3,75 we want)
            # We must scope the regex to "interest_rates" to avoid matching archive.
            m_section = re.search(
                r'"interest_rates"\s*:\s*"((?:[^"\\]|\\.)*)"',
                html,
                re.DOTALL,
            )
            if m_section:
                section = m_section.group(1)
                m = re.search(
                    r'id=\\"ref\\".*?oprocentowanie=\\"(\d{1,2}[,\.]\d{2})\\"',
                    section,
                    re.DOTALL,
                )
                if m:
                    rate_pct = float(m.group(1).replace(",", "."))
                    _LOGGER.debug("NBP reference rate: %.2f%%", rate_pct)
                    return rate_pct / 100.0

            _LOGGER.warning("Could not find NBP reference rate in page HTML")
            return 0.0

        except Exception as exc:  # noqa: BLE001
            _LOGGER.warning("Could not fetch NBP reference rate: %s", exc)
            return 0.0
