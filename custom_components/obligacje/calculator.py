"""Bond value calculator for Polish Treasury Bonds (Obligacje Skarbowe).

All rates are stored and passed as decimals (0.05 = 5 %).
CPI history keys are the year of the March GUS announcement.
"""
from __future__ import annotations

import calendar
from datetime import date
from typing import Any, NamedTuple

from .const import (
    BOND_CAPITALIZED,
    BOND_DURATION_YEARS,
    BOND_PERIOD_TYPE,
    PERIOD_ANNUAL,
    PERIOD_MONTHLY,
    PERIOD_SEMIANNUAL,
    PERIOD_SINGLE,
)


class BondPeriod(NamedTuple):
    start: date
    end: date
    annual_rate: float  # decimal, e.g. 0.05 for 5 %


# ── Date helpers ──────────────────────────────────────────────────────────────

def _is_leap(year: int) -> bool:
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


def _days_in_year(year: int) -> int:
    return 366 if _is_leap(year) else 365


def _add_months(d: date, months: int) -> date:
    """Add *months* to *d*, clamping to end-of-month when necessary."""
    total = d.month - 1 + months
    year = d.year + total // 12
    month = total % 12 + 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def _add_years(d: date, years: int) -> date:
    """Add *years* to *d* (handles Feb 29 → Feb 28)."""
    try:
        return d.replace(year=d.year + years)
    except ValueError:
        return date(d.year + years, 2, 28)


# ── Series parsing ────────────────────────────────────────────────────────────

def parse_series(series: str) -> tuple[str, int, int]:
    """Return (bond_type, maturity_month, maturity_year) from a series code.

    E.g. "EDO0130" → ("EDO", 1, 2030)
    """
    bond_type = series[:3].upper()
    maturity_month = int(series[3:5])
    maturity_year = 2000 + int(series[5:7])
    return bond_type, maturity_month, maturity_year


def derive_purchase_month_year(series: str) -> tuple[int, int]:
    """Estimate purchase month/year from the series code (no explicit date given).

    The maturity month/year is encoded in the series; duration is known per type.
    """
    bond_type, mat_month, mat_year = parse_series(series)
    if bond_type == "OTS":
        # 3 months before maturity
        m = mat_month - 3
        y = mat_year
        if m <= 0:
            m += 12
            y -= 1
        return m, y
    duration = BOND_DURATION_YEARS[bond_type]
    return mat_month, mat_year - duration


def derive_maturity_date(series: str, purchase_date: date) -> date:
    """Compute the exact maturity date.

    Day of maturity = day of purchase (clamped to end of month if needed).
    Month and year come from the series code.
    """
    _, mat_month, mat_year = parse_series(series)
    day = min(purchase_date.day, calendar.monthrange(mat_year, mat_month)[1])
    return date(mat_year, mat_month, day)


# ── Period building ───────────────────────────────────────────────────────────

def build_periods(
    bond_type: str,
    purchase_date: date,
    maturity_date: date,
    year1_rate: float,
    margin: float,
    cpi_history: dict[int, float],
    nbp_ref_rate: float,
) -> list[BondPeriod]:
    """Build the full list of interest periods for a bond.

    Args:
        bond_type:     e.g. "EDO", "COI", "ROR".
        purchase_date: exact date of purchase.
        maturity_date: exact date of maturity.
        year1_rate:    period-1 rate as decimal.
        margin:        margin added to index for periods 2+ (decimal).
        cpi_history:   {year: cpi_decimal} — GUS March announcements.
                       year = calendar year of the announcement.
        nbp_ref_rate:  current NBP reference rate as decimal.
                       Used for ROR/DOR/TOS/TOZ (historical rates not stored yet).
    """
    period_type = BOND_PERIOD_TYPE[bond_type]
    periods: list[BondPeriod] = []

    if period_type == PERIOD_SINGLE:
        periods.append(BondPeriod(purchase_date, maturity_date, year1_rate))
        return periods

    if period_type == PERIOD_ANNUAL:
        current = purchase_date
        period_num = 0
        while current < maturity_date:
            period_num += 1
            next_date = min(_add_years(current, 1), maturity_date)

            if period_num == 1:
                rate = year1_rate
            else:
                # GUS announces the prior year's CPI each March.
                # A period starting in month M of year Y uses:
                #   M >= 3 → CPI for year Y-1  (announced in March Y)
                #   M < 3  → CPI for year Y-2  (announced in March Y-1)
                cpi_year = current.year - 1 if current.month >= 3 else current.year - 2
                cpi = cpi_history.get(cpi_year, 0.0)
                rate = max(0.0, cpi) + margin

            periods.append(BondPeriod(current, next_date, rate))
            current = next_date
        return periods

    if period_type == PERIOD_MONTHLY:
        current = purchase_date
        period_num = 0
        while current < maturity_date:
            period_num += 1
            next_date = min(_add_months(current, 1), maturity_date)
            rate = year1_rate if period_num == 1 else max(
                0.0, nbp_ref_rate) + margin
            periods.append(BondPeriod(current, next_date, rate))
            current = next_date
        return periods

    if period_type == PERIOD_SEMIANNUAL:
        current = purchase_date
        period_num = 0
        while current < maturity_date:
            period_num += 1
            next_date = min(_add_months(current, 6), maturity_date)
            # TOZ uses WIBOR 6M; approximate with NBP ref rate
            rate = year1_rate if period_num == 1 else max(
                0.0, nbp_ref_rate) + margin
            periods.append(BondPeriod(current, next_date, rate))
            current = next_date
        return periods

    return periods


# ── Main calculation ──────────────────────────────────────────────────────────

def calculate_bond_value(
    series: str,
    purchase_date: date,
    quantity: int,
    year1_rate: float,
    margin: float,
    cpi_history: dict[int, float],
    nbp_ref_rate: float,
    today: date | None = None,
) -> dict[str, Any]:
    """Calculate current value of a bond position.

    Returns a dict with keys matching SENSOR_* constants:
        current_value, purchase_value, profit_loss,
        current_rate (%), accrued_interest, maturity_date, days_to_maturity.
    """
    if today is None:
        today = date.today()

    bond_type, _, _ = parse_series(series)
    maturity_date = derive_maturity_date(series, purchase_date)
    capitalized = BOND_CAPITALIZED[bond_type]
    purchase_value = 100.0 * quantity
    days_to_maturity = (maturity_date - today).days

    if today >= maturity_date:
        return {
            "current_value": round(purchase_value, 2),
            "purchase_value": round(purchase_value, 2),
            "profit_loss": 0.0,
            "current_rate": 0.0,
            "accrued_interest": 0.0,
            "maturity_date": maturity_date,
            "days_to_maturity": 0,
        }

    periods = build_periods(
        bond_type, purchase_date, maturity_date,
        year1_rate, margin, cpi_history, nbp_ref_rate,
    )

    # Walk through periods and accumulate value per single bond (100 PLN nominal)
    base_value = 100.0          # grows for capitalized bonds
    # interest accrued in the current (partial) period
    accrued_per_bond = 0.0
    current_rate_pct = year1_rate * 100.0

    for period in periods:
        if today <= period.start:
            break  # future period — stop

        current_rate_pct = period.annual_rate * 100.0
        period_end_clamped = min(today, period.end)
        days_elapsed = (period_end_clamped - period.start).days
        year_days = _days_in_year(period.start.year)

        partial_interest = base_value * period.annual_rate * days_elapsed / year_days

        if period.end <= today:
            # Full period has elapsed
            full_days = (period.end - period.start).days
            full_interest = base_value * period.annual_rate * full_days / year_days
            if capitalized:
                # Bank rounds per-bond interest to 2 dp before adding to base
                base_value += round(full_interest, 2)
            # Non-capitalized: interest was paid out — reset accrued
            accrued_per_bond = 0.0
        else:
            # Partial (current) period — bank rounds per-bond, then × quantity
            accrued_per_bond = round(partial_interest, 2)

    # Bank computes per-bond, rounds, then multiplies
    current_value = (base_value + accrued_per_bond) * quantity
    profit_loss = current_value - purchase_value

    return {
        "current_value": round(current_value, 2),
        "purchase_value": round(purchase_value, 2),
        "profit_loss": round(profit_loss, 2),
        "current_rate": round(current_rate_pct, 4),
        "accrued_interest": round(accrued_per_bond * quantity, 2),
        "maturity_date": maturity_date,
        "days_to_maturity": max(0, days_to_maturity),
    }
