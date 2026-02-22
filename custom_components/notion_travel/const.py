"""Constants for the Notion Travel integration."""

from __future__ import annotations

from homeassistant.const import Platform

DOMAIN = "notion_travel"

API_BASE_URL = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"

CONF_TOKEN = "token"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_DATABASES = "databases"
CONF_ADDITIONAL_DATABASES = "additional_databases"

CONF_DB_TRIPS = "trips"
CONF_DB_FLIGHTS = "flights"
CONF_DB_LODGING = "lodging"
CONF_DB_TRANSPORTATION = "transportation"
CONF_DB_ACTIVITIES = "activities"
CONF_DB_DINING = "dining"
CONF_DB_NOTES = "notes"

DATA_CONFIG = "config"
DATA_COORDINATOR = "coordinator"

DEFAULT_SCAN_INTERVAL = 1800
MIN_SCAN_INTERVAL = 60

PLATFORMS = [Platform.SENSOR]

DOMAIN_LABELS = {
    CONF_DB_FLIGHTS: "Flights",
    CONF_DB_LODGING: "Lodging",
    CONF_DB_TRANSPORTATION: "Transportation",
    CONF_DB_ACTIVITIES: "Activities",
    CONF_DB_DINING: "Dining",
    CONF_DB_NOTES: "Notes",
}

ICON_BY_DOMAIN = {
    CONF_DB_FLIGHTS: "mdi:airplane",
    CONF_DB_LODGING: "mdi:bed",
    CONF_DB_TRANSPORTATION: "mdi:car",
    CONF_DB_ACTIVITIES: "mdi:hiking",
    CONF_DB_DINING: "mdi:silverware-fork-knife",
    CONF_DB_NOTES: "mdi:notebook-outline",
}
