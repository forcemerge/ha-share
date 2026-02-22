"""Data coordinator for the Notion Travel integration."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
import logging
from typing import Any

from aiohttp import ClientError

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import (
    API_BASE_URL,
    CONF_DB_ACTIVITIES,
    CONF_DB_DINING,
    CONF_DB_FLIGHTS,
    CONF_DB_LODGING,
    CONF_DB_NOTES,
    CONF_DB_TRANSPORTATION,
    CONF_DB_TRIPS,
    DOMAIN,
    ICON_BY_DOMAIN,
    NOTION_VERSION,
)
from .helpers import (
    extract_date_end,
    extract_date_start,
    extract_date_time_zone,
    extract_files,
    extract_multi_select,
    extract_number,
    extract_phone,
    extract_relation_ids,
    extract_rich_text,
    extract_select,
    extract_title,
    extract_url,
    get_property,
    parse_trip_relation_ids,
    safe_float,
)

_LOGGER = logging.getLogger(__name__)


class NotionTravelDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator to fetch and normalize Notion travel data."""

    def __init__(
        self,
        hass: HomeAssistant,
        token: str,
        databases: dict[str, str],
        scan_interval_seconds: int,
    ) -> None:
        """Initialize coordinator."""
        self._token = token
        self._databases = databases
        self._child_datasets = tuple(
            dataset for dataset in databases if dataset != CONF_DB_TRIPS
        )
        self._session = async_get_clientsession(hass)

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval_seconds),
        )

    @property
    def child_datasets(self) -> tuple[str, ...]:
        """Return configured non-trip datasets."""
        return self._child_datasets

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch latest data from all configured Notion databases."""
        try:
            raw = await self._fetch_all_databases()
            return self._normalize(raw)
        except UpdateFailed:
            raise
        except Exception as err:
            raise UpdateFailed(f"Unexpected Notion Travel update failure: {err}") from err

    async def _fetch_all_databases(self) -> dict[str, list[dict[str, Any]]]:
        """Fetch all rows from Trips + all child datasets."""
        datasets = list(self._databases.keys())
        tasks = [self._fetch_database_rows(self._databases[name]) for name in datasets]
        rows_by_dataset = await asyncio.gather(*tasks)
        return dict(zip(datasets, rows_by_dataset, strict=True))

    async def _fetch_database_rows(self, database_id: str) -> list[dict[str, Any]]:
        """Read all pages in a Notion database, handling pagination."""
        rows: list[dict[str, Any]] = []
        next_cursor: str | None = None

        while True:
            payload: dict[str, Any] = {}
            if next_cursor:
                payload["start_cursor"] = next_cursor

            response = await self._query_database(database_id, payload)
            rows.extend(response.get("results", []))

            if not response.get("has_more"):
                break

            next_cursor = response.get("next_cursor")
            if not next_cursor:
                break

        return rows

    async def _query_database(self, database_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Execute a Notion database query call."""
        url = f"{API_BASE_URL}/databases/{database_id}/query"
        headers = {
            "Authorization": f"Bearer {self._token}",
            "Notion-Version": NOTION_VERSION,
            "Content-Type": "application/json",
        }

        try:
            async with self._session.post(url, headers=headers, json=payload, timeout=30) as response:
                if response.status != 200:
                    body = await response.text()
                    raise UpdateFailed(
                        f"Notion API error ({response.status}) for database {database_id}: {body}"
                    )
                return await response.json()
        except ClientError as err:
            raise UpdateFailed(f"Notion API connection error for database {database_id}: {err}") from err

    def _normalize(self, raw: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
        """Normalize raw Notion pages into HA-friendly structures."""
        trips: list[dict[str, Any]] = []
        trip_index: dict[str, dict[str, Any]] = {}

        for page in raw.get(CONF_DB_TRIPS, []):
            trip = self._parse_trip_page(page)
            trip["items"] = {dataset: [] for dataset in self._child_datasets}
            trip["counts"] = {dataset: 0 for dataset in self._child_datasets}
            trip["total_cost"] = 0.0
            trips.append(trip)
            trip_index[trip["id"]] = trip

        for dataset in self._child_datasets:
            for page in raw.get(dataset, []):
                item = self._parse_child_page(dataset, page)
                trip_ids: list[str] = item.pop("trip_ids", [])

                for trip_id in trip_ids:
                    trip = trip_index.get(trip_id)
                    if not trip:
                        continue
                    trip["items"][dataset].append(item)

        for trip in trips:
            running_total = 0.0
            for dataset in self._child_datasets:
                items = trip["items"][dataset]
                trip["counts"][dataset] = len(items)
                for item in items:
                    cost = safe_float(item.get("cost"))
                    if cost is not None:
                        running_total += cost
            trip["total_cost"] = round(running_total, 2)
            timeline_events = self._build_timeline_events(trip)
            trip["timeline_events"] = timeline_events
            trip["timeline_events_upcoming"] = self._filter_upcoming_events(timeline_events)

        trips.sort(key=self._trip_sort_key)
        next_trip_id = self._find_next_trip_id(trips)

        return {
            "trips": trips,
            "trip_index": trip_index,
            "next_trip_id": next_trip_id,
            "last_update": dt_util.utcnow().isoformat(),
        }

    def _parse_trip_page(self, page: dict[str, Any]) -> dict[str, Any]:
        """Parse one page from the Trips database."""
        properties = page.get("properties", {})

        dates_prop = get_property(properties, "Dates", "Date")

        return {
            "id": page.get("id", ""),
            "name": extract_title(get_property(properties, "Name", "Title")) or "Untitled Trip",
            "destination": extract_rich_text(get_property(properties, "Destination")),
            "status": extract_select(get_property(properties, "Status")),
            "tags": extract_multi_select(get_property(properties, "Tags")),
            "start_date": extract_date_start(dates_prop),
            "end_date": extract_date_end(dates_prop),
            "budget": extract_number(get_property(properties, "Budget")),
            "latitude": extract_number(get_property(properties, "Latitude")),
            "longitude": extract_number(get_property(properties, "Longitude")),
            "notes": extract_rich_text(get_property(properties, "Notes")),
            "cover_images": extract_files(get_property(properties, "Cover Image", "Cover")),
            "url": page.get("url", ""),
            "last_edited_time": page.get("last_edited_time"),
        }

    def _parse_child_page(self, dataset: str, page: dict[str, Any]) -> dict[str, Any]:
        """Parse one page from a child dataset."""
        properties = page.get("properties", {})

        item: dict[str, Any] = {
            "id": page.get("id", ""),
            "name": extract_title(get_property(properties, "Name", "Title")) or "Untitled",
            "status": extract_select(get_property(properties, "Status")),
            "notes": extract_rich_text(get_property(properties, "Notes")),
            "notion_url": page.get("url", ""),
            "external_url": extract_url(
                get_property(properties, "URL", "Website", "Map Link", "Reference URL")
            ),
            "trip_ids": parse_trip_relation_ids(page),
            "last_edited_time": page.get("last_edited_time"),
        }

        if dataset == CONF_DB_FLIGHTS:
            departure_time_prop = get_property(properties, "Departure Time")
            arrival_time_prop = get_property(properties, "Arrival Time")
            item.update(
                {
                    "airline": self._select_or_text(get_property(properties, "Airline")),
                    "flight_number": extract_rich_text(get_property(properties, "Flight Number")),
                    "departure_airport": extract_rich_text(get_property(properties, "Departure Airport")),
                    "arrival_airport": extract_rich_text(get_property(properties, "Arrival Airport")),
                    "departure_time": extract_date_start(departure_time_prop),
                    "arrival_time": extract_date_start(arrival_time_prop),
                    "departure_time_zone": extract_date_time_zone(departure_time_prop),
                    "arrival_time_zone": extract_date_time_zone(arrival_time_prop),
                    "class": extract_select(get_property(properties, "Class")),
                    "seat": extract_rich_text(get_property(properties, "Seat")),
                    "confirmation": extract_rich_text(
                        get_property(
                            properties,
                            "Confirmation",
                            "Confirmation Number",
                            "Record Locator",
                            "PNR",
                        )
                    ),
                    "cost": extract_number(get_property(properties, "Cost")),
                }
            )

        elif dataset == CONF_DB_LODGING:
            check_in_prop = get_property(properties, "Check In", "Check-In")
            check_out_prop = get_property(properties, "Check Out", "Check-Out")
            item.update(
                {
                    "address": extract_rich_text(get_property(properties, "Address")),
                    "check_in": extract_date_start(check_in_prop),
                    "check_out": extract_date_start(check_out_prop),
                    "check_in_time_zone": extract_date_time_zone(check_in_prop),
                    "check_out_time_zone": extract_date_time_zone(check_out_prop),
                    "confirmation": extract_rich_text(
                        get_property(
                            properties,
                            "Confirmation",
                            "Confirmation Number",
                            "Reservation Number",
                            "Reservation",
                            "Booking Number",
                        )
                    ),
                    "cost": extract_number(get_property(properties, "Cost Per Night", "Cost")),
                    "phone": extract_phone(get_property(properties, "Phone")),
                    "website": extract_url(get_property(properties, "URL", "Website", "Map Link")),
                }
            )

        elif dataset == CONF_DB_TRANSPORTATION:
            start_time_prop = get_property(properties, "Start Time")
            end_time_prop = get_property(properties, "End Time")
            item.update(
                {
                    "type": extract_select(get_property(properties, "Type")),
                    "company": self._select_or_text(get_property(properties, "Company")),
                    "vehicle_type": extract_select(get_property(properties, "Vehicle Type")),
                    "confirmation": extract_rich_text(
                        get_property(
                            properties,
                            "Confirmation",
                            "Confirmation Number",
                            "Reservation Number",
                            "Reservation",
                            "Booking Number",
                        )
                    ),
                    "start_time": extract_date_start(start_time_prop),
                    "end_time": extract_date_start(end_time_prop),
                    "start_time_zone": extract_date_time_zone(start_time_prop),
                    "end_time_zone": extract_date_time_zone(end_time_prop),
                    "start_location": extract_rich_text(get_property(properties, "Start Location")),
                    "end_location": extract_rich_text(get_property(properties, "End Location")),
                    "website": extract_url(get_property(properties, "URL", "Website", "Map Link")),
                    "cost": extract_number(get_property(properties, "Cost")),
                }
            )

        elif dataset == CONF_DB_ACTIVITIES:
            start_time_prop = get_property(properties, "Start Time")
            end_time_prop = get_property(properties, "End Time")
            item.update(
                {
                    "category": extract_select(get_property(properties, "Category")),
                    "start_time": extract_date_start(start_time_prop),
                    "end_time": extract_date_start(end_time_prop),
                    "start_time_zone": extract_date_time_zone(start_time_prop),
                    "end_time_zone": extract_date_time_zone(end_time_prop),
                    "duration": extract_rich_text(get_property(properties, "Duration")),
                    "location": extract_rich_text(get_property(properties, "Location")),
                    "cost": extract_number(get_property(properties, "Cost")),
                    "website": extract_url(get_property(properties, "URL", "Website", "Map Link")),
                }
            )

        elif dataset == CONF_DB_DINING:
            reservation_time_prop = get_property(properties, "Date/Time", "Reservation Time", "Reservation")
            item.update(
                {
                    "cuisine_type": extract_select(get_property(properties, "Cuisine Type", "Cuisine")),
                    "meal_type": extract_select(get_property(properties, "Meal Type")),
                    "location": extract_rich_text(get_property(properties, "Location")),
                    "phone": extract_phone(get_property(properties, "Phone")),
                    "reservation_time": extract_date_start(reservation_time_prop),
                    "date_time": extract_date_start(reservation_time_prop),
                    "reservation_time_zone": extract_date_time_zone(reservation_time_prop),
                    "date_time_time_zone": extract_date_time_zone(reservation_time_prop),
                    "cost": extract_number(get_property(properties, "Cost")),
                    "priority": extract_select(get_property(properties, "Priority")),
                    "confirmation": extract_rich_text(
                        get_property(
                            properties,
                            "Reservation Number",
                            "Confirmation",
                            "Confirmation Number",
                            "Reservation ID",
                            "Booking ID",
                        )
                    ),
                    "website": extract_url(get_property(properties, "URL", "Website", "Map Link")),
                }
            )

        elif dataset == CONF_DB_NOTES:
            date_relevant_prop = get_property(properties, "Date Relevant", "Date")
            item.update(
                {
                    "category": extract_select(get_property(properties, "Category")),
                    "priority": extract_select(get_property(properties, "Priority")),
                    "date_relevant": extract_date_start(date_relevant_prop),
                    "date_relevant_time_zone": extract_date_time_zone(date_relevant_prop),
                    "content": extract_rich_text(get_property(properties, "Content", "Notes")),
                    "reference_url": extract_url(
                        get_property(properties, "URL", "Reference URL", "Map Link", "Website")
                    ),
                    "cost": extract_number(get_property(properties, "Cost")),
                }
            )
        else:
            item.update(
                {
                    "cost": extract_number(
                        get_property(
                            properties,
                            "Cost",
                            "Price",
                            "Amount",
                            "Estimated Cost",
                        )
                    ),
                    "properties": self._parse_generic_properties(properties),
                }
            )

        # Add raw relation IDs from child page for debugging/troubleshooting.
        item["relation_ids"] = parse_trip_relation_ids(page)
        return item

    def _select_or_text(self, prop: dict[str, Any]) -> str:
        """Extract select text first, then rich text fallback."""
        return extract_select(prop) or extract_rich_text(prop)

    def _build_timeline_events(self, trip: dict[str, Any]) -> list[dict[str, Any]]:
        """Create one chronological cross-dataset event stream for a trip."""
        events: list[dict[str, Any]] = []
        items_by_dataset = trip.get("items", {})

        for dataset in self._child_datasets:
            for item in items_by_dataset.get(dataset, []):
                event = self._build_timeline_event(dataset, item)
                if event is not None:
                    events.append(event)

        events.sort(key=self._timeline_sort_key)
        return events

    def _filter_upcoming_events(self, events: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Return timeline events that are upcoming/active from now onward."""
        now = dt_util.utcnow()
        upcoming: list[dict[str, Any]] = []

        for event in events:
            start = self._parse_datetime(event.get("start"))
            end = self._parse_datetime(event.get("end"))
            if start and start >= now:
                upcoming.append(event)
                continue
            if end and end >= now:
                upcoming.append(event)
                continue

        return upcoming

    def _build_timeline_event(self, dataset: str, item: dict[str, Any]) -> dict[str, Any] | None:
        """Normalize one child item into a timeline event model."""
        start, end = self._event_window(dataset, item)
        time_zone = self._event_time_zone(dataset, item)

        return {
            "id": item.get("id"),
            "dataset": dataset,
            "title": item.get("name", "Untitled"),
            "subtitle": self._event_subtitle(dataset, item),
            "status": item.get("status"),
            "location": self._event_location(dataset, item),
            "start": start,
            "end": end,
            "time_zone": time_zone,
            "cost": item.get("cost"),
            "seat": item.get("seat"),
            "icon": ICON_BY_DOMAIN.get(dataset, "mdi:calendar-star"),
            "url": item.get("website") or item.get("reference_url") or item.get("external_url"),
            "notion_url": item.get("notion_url") or item.get("url"),
            "confirmation": item.get("confirmation"),
            "content": item.get("content") or item.get("notes"),
            "last_edited_time": item.get("last_edited_time"),
        }

    def _event_window(self, dataset: str, item: dict[str, Any]) -> tuple[str | None, str | None]:
        """Return start/end datetime strings for known datasets with fallback keys."""
        start_keys: dict[str, tuple[str, ...]] = {
            CONF_DB_FLIGHTS: ("departure_time", "arrival_time"),
            CONF_DB_LODGING: ("check_in", "check_out"),
            CONF_DB_TRANSPORTATION: ("start_time", "end_time"),
            CONF_DB_ACTIVITIES: ("start_time", "end_time"),
            CONF_DB_DINING: ("reservation_time", "date_time", "start_time"),
            CONF_DB_NOTES: ("date_relevant",),
        }
        end_keys: dict[str, tuple[str, ...]] = {
            CONF_DB_FLIGHTS: ("arrival_time",),
            CONF_DB_LODGING: ("check_out",),
            CONF_DB_TRANSPORTATION: ("end_time",),
            CONF_DB_ACTIVITIES: ("end_time",),
            CONF_DB_DINING: (),
            CONF_DB_NOTES: (),
        }

        generic_start = ("start_time", "date_time", "start_date", "date")
        generic_end = ("end_time", "end_date")

        start = self._first_non_empty(item, *(start_keys.get(dataset, ()) + generic_start))
        end = self._first_non_empty(item, *(end_keys.get(dataset, ()) + generic_end))
        return start, end

    def _event_time_zone(self, dataset: str, item: dict[str, Any]) -> str | None:
        """Return configured timezone for the event when provided by Notion."""
        time_zone_keys: dict[str, tuple[str, ...]] = {
            CONF_DB_FLIGHTS: ("departure_time_zone", "arrival_time_zone"),
            CONF_DB_LODGING: ("check_in_time_zone", "check_out_time_zone"),
            CONF_DB_TRANSPORTATION: ("start_time_zone", "end_time_zone"),
            CONF_DB_ACTIVITIES: ("start_time_zone", "end_time_zone"),
            CONF_DB_DINING: ("reservation_time_zone", "date_time_time_zone", "start_time_zone"),
            CONF_DB_NOTES: ("date_relevant_time_zone",),
        }

        generic_time_zone_keys = (
            "start_time_zone",
            "date_time_time_zone",
            "start_date_time_zone",
            "date_time_zone",
            "end_time_zone",
            "end_date_time_zone",
        )

        return self._first_non_empty(item, *(time_zone_keys.get(dataset, ()) + generic_time_zone_keys))

    def _first_non_empty(self, source: dict[str, Any], *keys: str) -> str | None:
        """Return first non-empty string value from known keys."""
        for key in keys:
            value = source.get(key)
            if isinstance(value, str) and value:
                return value
        return None

    def _event_subtitle(self, dataset: str, item: dict[str, Any]) -> str:
        """Return a concise secondary label for timeline display."""
        if dataset == CONF_DB_FLIGHTS:
            airline = item.get("airline")
            flight_number = item.get("flight_number")
            if airline and flight_number:
                return f"{airline} {flight_number}"
            return airline or flight_number or "Flight"

        if dataset == CONF_DB_LODGING:
            return item.get("room_type") or "Stay"

        if dataset == CONF_DB_TRANSPORTATION:
            parts = [item.get("type"), item.get("company")]
            return " • ".join(part for part in parts if part) or "Transportation"

        if dataset == CONF_DB_ACTIVITIES:
            return item.get("category") or "Activity"

        if dataset == CONF_DB_DINING:
            parts = [item.get("meal_type"), item.get("cuisine_type")]
            return " • ".join(part for part in parts if part) or "Dining"

        if dataset == CONF_DB_NOTES:
            return item.get("category") or "Note"

        return dataset.replace("_", " ").title()

    def _event_location(self, dataset: str, item: dict[str, Any]) -> str:
        """Return best-effort location string by dataset."""
        if dataset == CONF_DB_FLIGHTS:
            dep = item.get("departure_airport")
            arr = item.get("arrival_airport")
            if dep and arr:
                return f"{dep} → {arr}"

        if dataset == CONF_DB_TRANSPORTATION:
            start_loc = item.get("start_location")
            end_loc = item.get("end_location")
            if start_loc and end_loc:
                return f"{start_loc} → {end_loc}"
            if start_loc:
                return start_loc
            if end_loc:
                return end_loc

        return (
            item.get("location")
            or item.get("address")
            or item.get("start_location")
            or item.get("end_location")
            or ""
        )

    def _timeline_sort_key(self, event: dict[str, Any]) -> tuple[datetime, str]:
        """Sort timeline events by their best available datetime."""
        event_dt = (
            self._parse_datetime(event.get("start"))
            or self._parse_datetime(event.get("end"))
            or self._parse_datetime(event.get("last_edited_time"))
            or datetime.max.replace(tzinfo=dt_util.UTC)
        )
        return (event_dt, str(event.get("title") or ""))

    def _find_next_trip_id(self, trips: list[dict[str, Any]]) -> str | None:
        """Find the nearest trip that is in-progress/upcoming based on start date."""
        now = dt_util.utcnow()
        candidates: list[tuple[datetime, str]] = []

        for trip in trips:
            start = self._parse_datetime(trip.get("start_date"))
            end = self._parse_datetime(trip.get("end_date")) or start
            if start is None:
                continue

            if end and end < now:
                continue

            candidates.append((start, trip["id"]))

        if not candidates:
            return trips[0]["id"] if trips else None

        candidates.sort(key=lambda item: item[0])
        return candidates[0][1]

    def _parse_generic_properties(self, properties: dict[str, Any]) -> dict[str, Any]:
        """Parse unknown dataset properties into JSON-safe primitives."""
        parsed: dict[str, Any] = {}

        for name, prop in properties.items():
            prop_type = prop.get("type")
            if prop_type == "title":
                parsed[name] = extract_title(prop)
            elif prop_type == "rich_text":
                parsed[name] = extract_rich_text(prop)
            elif prop_type == "select":
                parsed[name] = extract_select(prop)
            elif prop_type == "multi_select":
                parsed[name] = extract_multi_select(prop)
            elif prop_type == "number":
                parsed[name] = extract_number(prop)
            elif prop_type == "date":
                parsed[name] = {
                    "start": extract_date_start(prop),
                    "end": extract_date_end(prop),
                }
            elif prop_type == "relation":
                parsed[name] = extract_relation_ids(prop)
            elif prop_type == "phone_number":
                parsed[name] = extract_phone(prop)
            elif prop_type == "url":
                parsed[name] = extract_url(prop)
            elif prop_type == "files":
                parsed[name] = extract_files(prop)
            elif prop_type == "checkbox":
                parsed[name] = bool(prop.get("checkbox"))
            elif prop_type == "email":
                parsed[name] = prop.get("email")
            else:
                parsed[name] = prop.get(prop_type)

        return parsed

    def _trip_sort_key(self, trip: dict[str, Any]) -> datetime:
        """Sort trips by start date, falling back to very-future for undated trips."""
        value = self._parse_datetime(trip.get("start_date"))
        if value is None:
            return datetime.max.replace(tzinfo=dt_util.UTC)
        return value

    def _parse_datetime(self, value: str | None) -> datetime | None:
        """Parse Notion date/date-time values to timezone-aware datetime."""
        if not value:
            return None

        formatted = value.replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(formatted)
        except ValueError:
            return None

        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=dt_util.UTC)

        return parsed.astimezone(dt_util.UTC)
