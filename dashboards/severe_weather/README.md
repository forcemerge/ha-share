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

### AI snapshot helper entities required

This dashboard/script pattern expects these helper entities in your HA config:

- `input_text.storm_ai_snapshot_summary`
- `input_text.storm_ai_snapshot_confidence`
- `input_text.storm_ai_snapshot_watch_window`
- `input_text.storm_ai_snapshot_recommended_action`
- `input_number.storm_ai_snapshot_interval_minutes` (default `60`)
- `input_datetime.storm_ai_snapshot_last_updated`

The AI blurb card is always visible, shows a first-run message when no snapshot has run yet,
and manual tap-to-refresh still forces an on-demand update.

The included script uses broad weather context (NWS + storm helper sensors + local weather +
lightning metrics) while instructing the model to ignore unknown/unavailable values.

## Sanitization notes

This share package redacts environment-specific identifiers and uses neutral local sensor names.

The included `scripts.yaml` is also sanitized and expects your local AI task/weather entities.

Update these entities to match your own installation.

## Screenshot

Place your screenshot at:

- `images/dashboard.png`

![Dashboard screenshot](images/dashboard.png)
