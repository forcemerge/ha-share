# Severe Weather (v1)

Original Severe Weather dashboard snapshot package, preserved for comparison.

## Files

- `dashboard.yaml` - sanitized v1 dashboard definition
- `helpers.yaml` - helper template and binary sensors used by this dashboard
- `images/dashboard.png` - add one screenshot here

## Requirements

- NWS Alerts integration + `custom:nws-alert-card`
- Mushroom cards
- ApexCharts card
- Script entity: `script.severe_weather_ai_correlation_snapshot` (or equivalent)

## Sanitization notes

This package redacts environment-specific identifiers and replaces them with neutral names:

- `sensor.st_louis_lightning_count_last_1_hr` -> `sensor.local_lightning_count_last_1_hr`
- `sensor.st_louis_lightning_count_last_3_hr` -> `sensor.local_lightning_count_last_3_hr`
- `sensor.st_00201644_lightning_average_distance` -> `sensor.local_lightning_average_distance`
- `sensor.st_00201644_wind_gust` -> `sensor.local_weather_wind_gust`
- `sensor.st_louis_pressure_sea_level` -> `sensor.local_weather_pressure_sea_level`
- `sensor.st_louis_rain_last_hour` -> `sensor.local_weather_rain_last_hour`

Update these entities to your local equivalents before use.

## Screenshot

Place your screenshot at:

- `images/dashboard.png`
