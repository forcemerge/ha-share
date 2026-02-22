"""Sensor platform for the Notion Travel integration."""

from __future__ import annotations

from datetime import datetime
import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.const import CURRENCY_DOLLAR
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import (
    CONF_ADDITIONAL_DATABASES,
    CONF_DATABASES,
    CONF_SCAN_INTERVAL,
    CONF_TOKEN,
    DATA_CONFIG,
    DATA_COORDINATOR,
    DOMAIN,
    DOMAIN_LABELS,
    ICON_BY_DOMAIN,
)
from .coordinator import NotionTravelDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up Notion Travel sensors from YAML config."""
    domain_data = hass.data.setdefault(DOMAIN, {})
    cfg = domain_data.get(DATA_CONFIG)

    if not cfg:
        _LOGGER.error("%s config missing in hass.data", DOMAIN)
        return

    coordinator: NotionTravelDataUpdateCoordinator | None = domain_data.get(DATA_COORDINATOR)
    if coordinator is None:
        databases = dict(cfg[CONF_DATABASES])
        databases.update(cfg.get(CONF_ADDITIONAL_DATABASES, {}))

        coordinator = NotionTravelDataUpdateCoordinator(
            hass=hass,
            token=cfg[CONF_TOKEN],
            databases=databases,
            scan_interval_seconds=cfg[CONF_SCAN_INTERVAL],
        )
        domain_data[DATA_COORDINATOR] = coordinator
        await coordinator.async_refresh()

    if not coordinator.last_update_success:
        _LOGGER.error("Initial %s refresh failed; entities not added", DOMAIN)
        return

    _remove_legacy_trip_entities(hass)

    initial_entities = _build_entities_for_dataset(coordinator, coordinator.data)
    async_add_entities(initial_entities)


def _build_entities_for_dataset(
    coordinator: NotionTravelDataUpdateCoordinator, data: dict[str, Any]
) -> list[SensorEntity]:
    _ = data
    return [NotionTravelNextTripSensor(coordinator)]


def _remove_legacy_trip_entities(hass: HomeAssistant) -> None:
    """Remove legacy trip-specific entities from registry.

    The Phase 2 UX intentionally focuses on one generalized next-trip sensor.
    """
    registry = er.async_get(hass)
    removed = 0

    for entry in list(registry.entities.values()):
        if entry.platform != DOMAIN:
            continue

        unique_id = entry.unique_id or ""
        if unique_id == "notion_travel_next_trip":
            continue
        if not unique_id.startswith("notion_travel_"):
            continue

        registry.async_remove(entry.entity_id)
        removed += 1

    if removed:
        _LOGGER.info("Removed %d legacy Notion Travel trip-specific entities", removed)


def _build_entities_for_trip(
    coordinator: NotionTravelDataUpdateCoordinator, trip: dict[str, Any]
) -> list[SensorEntity]:
    trip_id = trip.get("id", "")
    trip_name = trip.get("name", "Untitled Trip")

    entities: list[SensorEntity] = [
        NotionTravelTripSummarySensor(coordinator, trip_id, trip_name),
        NotionTravelTripTotalCostSensor(coordinator, trip_id, trip_name),
    ]

    for dataset in coordinator.child_datasets:
        entities.append(
            NotionTravelTripDomainCountSensor(coordinator, trip_id, trip_name, dataset)
        )

    return entities


class NotionTravelBaseSensor(CoordinatorEntity[NotionTravelDataUpdateCoordinator], SensorEntity):
    """Shared base class for Notion Travel sensors."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: NotionTravelDataUpdateCoordinator) -> None:
        """Initialize base class."""
        super().__init__(coordinator)


class NotionTravelNextTripSensor(NotionTravelBaseSensor):
    """Sensor for the next or in-progress trip."""

    _attr_name = "Next Trip"
    _attr_unique_id = "notion_travel_next_trip"
    _attr_icon = "mdi:airplane-takeoff"

    def __init__(self, coordinator: NotionTravelDataUpdateCoordinator) -> None:
        """Initialize next trip sensor."""
        super().__init__(coordinator)

    @property
    def native_value(self) -> str:
        """Return next trip name."""
        trip = self._next_trip()
        if not trip:
            return "No trips"
        return trip.get("name", "Untitled Trip")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return next-trip details."""
        trip = self._next_trip()
        if not trip:
            return {}

        timeline_events = trip.get("timeline_events", [])
        upcoming_events = trip.get("timeline_events_upcoming", [])
        next_event = upcoming_events[0] if upcoming_events else (timeline_events[0] if timeline_events else None)

        return {
            "trip_id": trip.get("id"),
            "destination": trip.get("destination"),
            "status": trip.get("status"),
            "tags": trip.get("tags", []),
            "start_date": trip.get("start_date"),
            "end_date": trip.get("end_date"),
            "days_until_start": _days_until(trip.get("start_date")),
            "budget": trip.get("budget"),
            "total_cost": trip.get("total_cost"),
            "counts": trip.get("counts", {}),
            "timeline_event_count": len(timeline_events),
            "timeline_upcoming_count": len(upcoming_events),
            "timeline_events": timeline_events,
            "timeline_events_upcoming": upcoming_events,
            "next_event": next_event,
            "url": trip.get("url"),
        }

    def _next_trip(self) -> dict[str, Any] | None:
        data = self.coordinator.data or {}
        next_trip_id = data.get("next_trip_id")
        trip_index = data.get("trip_index", {})
        if next_trip_id:
            return trip_index.get(next_trip_id)
        return None


class NotionTravelTripSensor(NotionTravelBaseSensor):
    """Shared base class for trip-specific sensors."""

    def __init__(
        self,
        coordinator: NotionTravelDataUpdateCoordinator,
        trip_id: str,
        trip_name: str,
    ) -> None:
        """Initialize trip sensor."""
        super().__init__(coordinator)
        self._trip_id = trip_id
        self._trip_name = trip_name

    def _trip(self) -> dict[str, Any]:
        data = self.coordinator.data or {}
        trip_index = data.get("trip_index", {})
        return trip_index.get(self._trip_id, {})


class NotionTravelTripSummarySensor(NotionTravelTripSensor):
    """Summary sensor for one trip."""

    _attr_icon = "mdi:map-marker-path"

    def __init__(
        self,
        coordinator: NotionTravelDataUpdateCoordinator,
        trip_id: str,
        trip_name: str,
    ) -> None:
        """Initialize trip summary sensor."""
        super().__init__(coordinator, trip_id, trip_name)
        self._attr_name = f"{trip_name}"
        self._attr_unique_id = f"notion_travel_{self._trip_id}_summary"

    @property
    def native_value(self) -> str:
        """Return trip status."""
        return self._trip().get("status") or "Unknown"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return summary attributes for one trip."""
        trip = self._trip()
        timeline_events = trip.get("timeline_events", [])
        upcoming_events = trip.get("timeline_events_upcoming", [])
        next_event = upcoming_events[0] if upcoming_events else (timeline_events[0] if timeline_events else None)

        return {
            "trip_id": trip.get("id"),
            "destination": trip.get("destination"),
            "start_date": trip.get("start_date"),
            "end_date": trip.get("end_date"),
            "days_until_start": _days_until(trip.get("start_date")),
            "tags": trip.get("tags", []),
            "budget": trip.get("budget"),
            "total_cost": trip.get("total_cost"),
            "counts": trip.get("counts", {}),
            "timeline_event_count": len(timeline_events),
            "timeline_upcoming_count": len(upcoming_events),
            "timeline_events": timeline_events,
            "timeline_events_upcoming": upcoming_events,
            "next_event": next_event,
            "notes": trip.get("notes"),
            "url": trip.get("url"),
            "last_edited_time": trip.get("last_edited_time"),
        }


class NotionTravelTripDomainCountSensor(NotionTravelTripSensor):
    """Count sensor for one child dataset under one trip."""

    def __init__(
        self,
        coordinator: NotionTravelDataUpdateCoordinator,
        trip_id: str,
        trip_name: str,
        dataset: str,
    ) -> None:
        """Initialize child-dataset count sensor."""
        super().__init__(coordinator, trip_id, trip_name)
        self._dataset = dataset
        dataset_label = DOMAIN_LABELS.get(dataset, dataset.title())
        self._attr_name = f"{trip_name} {dataset_label}"
        self._attr_unique_id = f"notion_travel_{self._trip_id}_{dataset}_count"
        self._attr_icon = ICON_BY_DOMAIN.get(dataset, "mdi:format-list-bulleted")

    @property
    def native_value(self) -> int:
        """Return number of child records for this dataset."""
        trip = self._trip()
        counts = trip.get("counts", {})
        return int(counts.get(self._dataset, 0))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return expanded child rows for this dataset."""
        trip = self._trip()
        items = trip.get("items", {}).get(self._dataset, [])
        return {
            "trip_id": trip.get("id"),
            "trip_name": trip.get("name"),
            "dataset": self._dataset,
            "count": len(items),
            "items": items,
        }


class NotionTravelTripTotalCostSensor(NotionTravelTripSensor):
    """Total aggregated cost sensor for one trip."""

    _attr_icon = "mdi:cash-multiple"
    _attr_native_unit_of_measurement = CURRENCY_DOLLAR
    _attr_suggested_display_precision = 2

    def __init__(
        self,
        coordinator: NotionTravelDataUpdateCoordinator,
        trip_id: str,
        trip_name: str,
    ) -> None:
        """Initialize trip total cost sensor."""
        super().__init__(coordinator, trip_id, trip_name)
        self._attr_name = f"{trip_name} Total Cost"
        self._attr_unique_id = f"notion_travel_{self._trip_id}_total_cost"

    @property
    def native_value(self) -> float:
        """Return aggregated cost for all child datasets in one trip."""
        trip = self._trip()
        value = trip.get("total_cost", 0.0)
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return budget/cost context."""
        trip = self._trip()
        budget = trip.get("budget")
        total = trip.get("total_cost", 0.0)

        remaining = None
        if isinstance(budget, (int, float)):
            remaining = round(float(budget) - float(total), 2)

        return {
            "trip_id": trip.get("id"),
            "trip_name": trip.get("name"),
            "budget": budget,
            "remaining_budget": remaining,
            "counts": trip.get("counts", {}),
        }


def _days_until(start_date: str | None) -> int | None:
    """Return number of days until start date."""
    if not start_date:
        return None

    start_dt = _parse_datetime(start_date)
    if start_dt is None:
        return None

    now = dt_util.now()
    start_local = dt_util.as_local(start_dt)
    now_local = dt_util.as_local(now)
    delta = start_local.date() - now_local.date()
    return delta.days


def _parse_datetime(value: str) -> datetime | None:
    """Parse Notion date/date-time strings."""
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt_util.UTC)

    return parsed
