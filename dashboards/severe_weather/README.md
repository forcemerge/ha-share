# Severe Weather

Current Severe Weather Command Center dashboard package.

## Files

- `dashboard.yaml` - sanitized current dashboard
- `helpers.yaml` - helper template and binary sensors used by this dashboard
- `images/dashboard.png` - add one screenshot here

## Requirements

- NWS Alerts integration + `custom:nws-alert-card`
- Mushroom cards
- ApexCharts card
- Blitzortung Lightning Card
- Script entity: `script.severe_weather_ai_correlation_snapshot` (or equivalent)

## Sanitization notes

This share package redacts environment-specific identifiers and uses neutral local sensor names.

Examples:

- `sensor.kennabrooke_lightning_*` -> `sensor.local_lightning_*`
- `sensor.st_00201644_wind_gust` -> `sensor.local_weather_wind_gust`
- `sensor.st_louis_pressure_sea_level` -> `sensor.local_weather_pressure_sea_level`
- `sensor.st_louis_rain_last_hour` -> `sensor.local_weather_rain_last_hour`

Update these entities to match your own installation.

## Screenshot

Place your screenshot at:

- `images/dashboard.png`
