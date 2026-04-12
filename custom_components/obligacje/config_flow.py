"""Config flow for Polskie Obligacje Skarbowe integration.

One config entry = one bond position (series + quantity + optional purchase date).
The user can add as many entries as they have different positions.

Flow:
  1. User enters series code  (e.g. "EDO0130")
  2. User enters quantity      (integer ≥ 1, each bond = 100 PLN)
  3. User enters purchase date (optional, YYYY-MM-DD;
                                if omitted, estimated from series code)
"""
from __future__ import annotations

import re
from datetime import date
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow

try:
    from homeassistant.config_entries import ConfigFlowResult  # HA ≥ 2024.8
except ImportError:
    # type: ignore[assignment]
    from homeassistant.data_entry_flow import FlowResult as ConfigFlowResult

from .const import (
    CONF_PURCHASE_DATE,
    CONF_QUANTITY,
    CONF_SERIES,
    DOMAIN,
    SERIES_PATTERN,
)

_SERIES_RE = re.compile(SERIES_PATTERN, re.IGNORECASE)


# ── Validators ────────────────────────────────────────────────────────────────

def _validate_series(raw: str) -> str:
    series = raw.strip().upper()
    if not _SERIES_RE.match(series):
        raise vol.Invalid("series_invalid")
    return series


def _validate_quantity(raw: Any) -> int:
    try:
        q = int(raw)
    except (TypeError, ValueError) as exc:
        raise vol.Invalid("quantity_invalid") from exc
    if q < 1:
        raise vol.Invalid("quantity_invalid")
    return q


def _validate_purchase_date(raw: str) -> str:
    """Accept empty string (optional) or a valid ISO date."""
    raw = raw.strip()
    if not raw:
        return ""
    try:
        date.fromisoformat(raw)
    except ValueError as exc:
        raise vol.Invalid("date_invalid") from exc
    return raw


# ── Flow ─────────────────────────────────────────────────────────────────────

class ObligacjeConfigFlow(ConfigFlow, domain=DOMAIN):
    """Single-step config flow for one bond position."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            series = user_input.get(CONF_SERIES, "")
            quantity_raw = user_input.get(CONF_QUANTITY, 1)
            purchase_date_raw = user_input.get(CONF_PURCHASE_DATE, "")

            try:
                series = _validate_series(str(series))
            except vol.Invalid:
                errors[CONF_SERIES] = "series_invalid"

            try:
                quantity = _validate_quantity(quantity_raw)
            except vol.Invalid:
                errors[CONF_QUANTITY] = "quantity_invalid"

            try:
                purchase_date = _validate_purchase_date(str(purchase_date_raw))
            except vol.Invalid:
                errors[CONF_PURCHASE_DATE] = "date_invalid"

            if not errors:
                unique_id = f"{series}_{purchase_date}" if purchase_date else series
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()

                title = f"{series} ×{quantity}"
                if purchase_date:
                    title += f" ({purchase_date})"

                return self.async_create_entry(
                    title=title,
                    data={
                        CONF_SERIES: series,
                        CONF_QUANTITY: quantity,
                        CONF_PURCHASE_DATE: purchase_date,
                    },
                )

        schema = vol.Schema(
            {
                vol.Required(CONF_SERIES): str,
                vol.Required(CONF_QUANTITY, default=1): int,
                vol.Optional(CONF_PURCHASE_DATE, default=""): str,
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )
