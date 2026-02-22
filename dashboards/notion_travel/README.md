# Notion Travel

Sanitized Notion Travel dashboard package using the custom `notion-travel-trip-card`.

## Files

- `dashboard.yaml` - single-pane trip console dashboard
- `images/dashboard.png` - add one screenshot here

## Requirements

- `notion_travel` custom integration (see `custom_components/notion_travel/` in this repo)
- Card resource `/local/notion-travel-trip-card.js`
- Sensor entity providing trip attributes (default: `sensor.notion_travel_next_trip`)

## Sanitization notes

- No Notion DB IDs, API tokens, hostnames, or location-specific values are embedded.
- Keep all credentials in HA `secrets.yaml`.

## Screenshot

Place your screenshot at:

- `images/dashboard.png`

![Dashboard screenshot](images/dashboard.png)
