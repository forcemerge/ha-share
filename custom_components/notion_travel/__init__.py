"""Notion Travel integration."""

from __future__ import annotations

import logging

import voluptuous as vol

from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.discovery import async_load_platform

from .const import (
    CONF_ADDITIONAL_DATABASES,
    CONF_DATABASES,
    CONF_DB_ACTIVITIES,
    CONF_DB_DINING,
    CONF_DB_FLIGHTS,
    CONF_DB_LODGING,
    CONF_DB_NOTES,
    CONF_DB_TRANSPORTATION,
    CONF_DB_TRIPS,
    CONF_SCAN_INTERVAL,
    CONF_TOKEN,
    DATA_CONFIG,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MIN_SCAN_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)

DATABASES_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_DB_TRIPS): cv.string,
        vol.Optional(CONF_DB_FLIGHTS): cv.string,
        vol.Optional(CONF_DB_LODGING): cv.string,
        vol.Optional(CONF_DB_TRANSPORTATION): cv.string,
        vol.Optional(CONF_DB_ACTIVITIES): cv.string,
        vol.Optional(CONF_DB_DINING): cv.string,
        vol.Optional(CONF_DB_NOTES): cv.string,
    }
)

ADDITIONAL_DATABASES_SCHEMA = vol.Schema({cv.string: cv.string})

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_TOKEN): cv.string,
                vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): vol.All(
                    vol.Coerce(int), vol.Range(min=MIN_SCAN_INTERVAL)
                ),
                vol.Required(CONF_DATABASES): DATABASES_SCHEMA,
                vol.Optional(CONF_ADDITIONAL_DATABASES, default={}): ADDITIONAL_DATABASES_SCHEMA,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the Notion Travel integration from YAML."""
    domain_config = config.get(DOMAIN)
    if not domain_config:
        return True

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][DATA_CONFIG] = domain_config

    _LOGGER.debug("Loaded %s YAML config and scheduling sensor platform", DOMAIN)
    hass.async_create_task(async_load_platform(hass, "sensor", DOMAIN, {}, config))
    return True
