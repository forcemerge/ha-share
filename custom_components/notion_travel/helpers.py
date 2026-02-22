"""Helper utilities for parsing Notion API payloads."""

from __future__ import annotations

from typing import Any


def _normalize_key(value: str) -> str:
    return value.strip().lower().replace(" ", "").replace("_", "")


def get_property(properties: dict[str, Any], *names: str) -> dict[str, Any]:
    """Return the first property matching one of the provided names."""
    if not properties:
        return {}

    for name in names:
        if name in properties:
            return properties[name]

    normalized_to_key = {_normalize_key(key): key for key in properties}
    for name in names:
        key = normalized_to_key.get(_normalize_key(name))
        if key:
            return properties[key]

    return {}


def extract_title(prop: dict[str, Any]) -> str:
    """Extract title text from a Notion title property."""
    if not prop:
        return ""

    blocks = prop.get("title", [])
    return "".join(block.get("plain_text", "") for block in blocks).strip()


def extract_rich_text(prop: dict[str, Any]) -> str:
    """Extract text from a Notion rich_text property."""
    if not prop:
        return ""

    blocks = prop.get("rich_text", [])
    return "".join(block.get("plain_text", "") for block in blocks).strip()


def extract_select(prop: dict[str, Any]) -> str:
    """Extract selected option name from a Notion select property."""
    if not prop:
        return ""

    select = prop.get("select")
    if not select:
        return ""
    return select.get("name", "")


def extract_multi_select(prop: dict[str, Any]) -> list[str]:
    """Extract selected option names from a Notion multi_select property."""
    if not prop:
        return []

    values = prop.get("multi_select", [])
    return [value.get("name", "") for value in values if value.get("name")]


def extract_number(prop: dict[str, Any]) -> float | int | None:
    """Extract numeric value from a Notion number property."""
    if not prop:
        return None
    return prop.get("number")


def extract_phone(prop: dict[str, Any]) -> str:
    """Extract phone number value."""
    if not prop:
        return ""
    return prop.get("phone_number") or ""


def extract_url(prop: dict[str, Any]) -> str:
    """Extract URL value."""
    if not prop:
        return ""
    return prop.get("url") or ""


def extract_date(prop: dict[str, Any]) -> dict[str, Any]:
    """Extract date payload from a Notion date property."""
    if not prop:
        return {}
    return prop.get("date") or {}


def extract_date_start(prop: dict[str, Any]) -> str | None:
    """Extract date.start from a Notion date property."""
    date_value = extract_date(prop)
    return date_value.get("start")


def extract_date_end(prop: dict[str, Any]) -> str | None:
    """Extract date.end from a Notion date property."""
    date_value = extract_date(prop)
    return date_value.get("end")


def extract_date_time_zone(prop: dict[str, Any]) -> str | None:
    """Extract date.time_zone from a Notion date property."""
    date_value = extract_date(prop)
    return date_value.get("time_zone")


def extract_relation_ids(prop: dict[str, Any]) -> list[str]:
    """Extract relation page IDs from a Notion relation property."""
    if not prop:
        return []

    relations = prop.get("relation", [])
    return [relation.get("id", "") for relation in relations if relation.get("id")]


def extract_files(prop: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract file metadata from a Notion files property."""
    if not prop:
        return []

    files = []
    for file_item in prop.get("files", []):
        file_type = file_item.get("type")
        url: str | None = None
        if file_type and isinstance(file_item.get(file_type), dict):
            url = file_item[file_type].get("url")

        files.append(
            {
                "name": file_item.get("name", ""),
                "type": file_type,
                "url": url,
            }
        )

    return files


def parse_trip_relation_ids(page: dict[str, Any]) -> list[str]:
    """Extract relation IDs for the trip relation from a child database record."""
    properties = page.get("properties", {})
    relation_prop = get_property(properties, "Trip", "Trips")
    relation_ids = extract_relation_ids(relation_prop)
    if relation_ids:
        return relation_ids

    relation_properties = [
        prop
        for prop in properties.values()
        if isinstance(prop, dict) and prop.get("type") == "relation"
    ]

    if len(relation_properties) == 1:
        return extract_relation_ids(relation_properties[0])

    return []


def safe_float(value: Any) -> float | None:
    """Convert value to float when possible."""
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
