# Notion Travel (Home Assistant Custom Integration)

Notion Travel syncs trip data from one Notion **Trips** database and any number of related child databases into Home Assistant sensors.

This integration is designed to be **schema-tolerant** and **public-share friendly**:

- Works across multiple trips, not just a single destination/use case
- Supports optional built-in child datasets (`flights`, `lodging`, etc.)
- Supports custom datasets via `additional_databases` without code changes
- Handles property naming variations (`Trip` vs `Trips`, etc.) where possible

## YAML Configuration

```yaml
notion_travel:
  token: !secret notion_travel_token
  scan_interval: 1800
  databases:
    trips: !secret notion_travel_db_trips
    flights: !secret notion_travel_db_flights
    lodging: !secret notion_travel_db_lodging
    transportation: !secret notion_travel_db_transportation
    activities: !secret notion_travel_db_activities
    dining: !secret notion_travel_db_dining
    notes: !secret notion_travel_db_notes
  additional_databases:
    packing: !secret notion_travel_db_packing
    weather: !secret notion_travel_db_weather
```

### Required keys

- `token`
- `databases.trips`

### Optional keys

- Standard child datasets under `databases` (`flights`, `lodging`, `transportation`, `activities`, `dining`, `notes`)
- Any custom child datasets under `additional_databases`

## Notion Requirements

1. All child databases should relate to your Trips database.
2. For best compatibility, include a relation property named `Trip` or `Trips`.
   - If there is exactly one relation property in a child database, it will be used automatically.
3. Use a title property (`Name`) in each database for readable sensor output.

## Entities Created

- `sensor.notion_travel_next_trip`
- Per trip:
  - Summary sensor (`sensor.notion_travel_<trip_id>_summary`)
  - Total cost sensor (`sensor.notion_travel_<trip_id>_total_cost`)
  - One count/detail sensor per configured child dataset

## Notes for Public Use

- Do not commit `secrets.yaml`
- Keep database IDs and API token in Home Assistant secrets
- Avoid assuming fixed property names in dashboards/automations; reference attributes defensively
