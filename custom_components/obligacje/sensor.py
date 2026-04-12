"""Sensor platform for Polskie Obligacje Skarbowe integration.

Each config entry (bond position) registers a device named after the series code.
Seven sensors are created per position:
  - Aktualna wartość     (current value, PLN)
  - Wartość zakupu       (purchase value, PLN)
  - Zysk / Strata        (profit or loss, PLN)
  - Oprocentowanie       (current period rate, %)
  - Narosłe odsetki      (accrued interest in current period, PLN)
  - Data wykupu          (maturity date)
  - Dni do wykupu        (days until maturity)
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_SERIES,
    DOMAIN,
    SENSOR_ACCRUED_INTEREST,
    SENSOR_CURRENT_RATE,
    SENSOR_CURRENT_VALUE,
    SENSOR_DAYS_TO_MATURITY,
    SENSOR_MATURITY_DATE,
    SENSOR_PROFIT_LOSS,
    SENSOR_PURCHASE_VALUE,
)
from .coordinator import ObligacjeCoordinator

_CURRENCY_PLN = "PLN"


@dataclass(frozen=True, kw_only=True)
class ObligacjeSensorDescription(SensorEntityDescription):
    """Extends SensorEntityDescription with a coordinator data key."""
    data_key: str


SENSOR_DESCRIPTIONS: tuple[ObligacjeSensorDescription, ...] = (
    ObligacjeSensorDescription(
        key=SENSOR_CURRENT_VALUE,
        data_key=SENSOR_CURRENT_VALUE,
        name="Aktualna wartość",
        icon="mdi:cash-multiple",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement=_CURRENCY_PLN,
        suggested_display_precision=2,
    ),
    ObligacjeSensorDescription(
        key=SENSOR_PURCHASE_VALUE,
        data_key=SENSOR_PURCHASE_VALUE,
        name="Wartość zakupu",
        icon="mdi:cash",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement=_CURRENCY_PLN,
        suggested_display_precision=2,
    ),
    ObligacjeSensorDescription(
        key=SENSOR_PROFIT_LOSS,
        data_key=SENSOR_PROFIT_LOSS,
        name="Zysk / Strata",
        icon="mdi:trending-up",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=_CURRENCY_PLN,
        suggested_display_precision=2,
    ),
    ObligacjeSensorDescription(
        key=SENSOR_CURRENT_RATE,
        data_key=SENSOR_CURRENT_RATE,
        name="Oprocentowanie bieżącego okresu",
        icon="mdi:percent",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        suggested_display_precision=2,
    ),
    ObligacjeSensorDescription(
        key=SENSOR_ACCRUED_INTEREST,
        data_key=SENSOR_ACCRUED_INTEREST,
        name="Narosłe odsetki",
        icon="mdi:finance",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=_CURRENCY_PLN,
        suggested_display_precision=2,
    ),
    ObligacjeSensorDescription(
        key=SENSOR_MATURITY_DATE,
        data_key=SENSOR_MATURITY_DATE,
        name="Data wykupu",
        icon="mdi:calendar-check",
        device_class=SensorDeviceClass.DATE,
    ),
    ObligacjeSensorDescription(
        key=SENSOR_DAYS_TO_MATURITY,
        data_key=SENSOR_DAYS_TO_MATURITY,
        name="Dni do wykupu",
        icon="mdi:calendar-clock",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="d",
        suggested_display_precision=0,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Create sensor entities for a bond position."""
    coordinator: ObligacjeCoordinator = hass.data[DOMAIN][entry.entry_id]
    series = entry.data[CONF_SERIES]
    async_add_entities(
        ObligacjeSensor(coordinator, description, series, entry.entry_id)
        for description in SENSOR_DESCRIPTIONS
    )


class ObligacjeSensor(CoordinatorEntity[ObligacjeCoordinator], SensorEntity):
    """One metric sensor for one bond position."""

    entity_description: ObligacjeSensorDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: ObligacjeCoordinator,
        description: ObligacjeSensorDescription,
        series: str,
        entry_id: str,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry_id}_{description.key}"
        bond_type = series[:3]
        self._attr_device_info = DeviceInfo(
            entry_type=DeviceEntryType.SERVICE,
            identifiers={(DOMAIN, entry_id)},
            name=series,
            manufacturer="Ministerstwo Finansów",
            model=bond_type,
        )

    @property
    def native_value(self) -> Any:
        if self.coordinator.data is None:
            return None
        value = self.coordinator.data.get(self.entity_description.data_key)
        # SensorDeviceClass.DATE accepts a date object directly
        return value
