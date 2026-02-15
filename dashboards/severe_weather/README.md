# Severe Weather

Current Severe Weather Command Center dashboard package.

## Files

- `dashboard.yaml` - sanitized current dashboard
- `helpers.yaml` - helper template and binary sensors used by this dashboard
- `scripts.yaml` - script referenced by dashboard action card
- `images/dashboard.png` - add one screenshot here

## Requirements

- NWS Alerts integration + `custom:nws-alert-card`
- Mushroom cards
- ApexCharts card
- Blitzortung Lightning Card
- Script entity: `script.severe_weather_ai_correlation_snapshot` (or equivalent)

## Sanitization notes

This share package redacts environment-specific identifiers and uses neutral local sensor names.

The included `scripts.yaml` is also sanitized and expects your local AI task/weather entities.

Update these entities to match your own installation.

## Screenshot

Place your screenshot at:

- `images/dashboard.png`

![Dashboard screenshot](images/dashboard.png)
