# Dashboards

Each subdirectory in this folder is a self-contained, shareable dashboard package.

## Required structure

```text
<dashboard_slug>/
  dashboard.yaml
  README.md
  images/
    dashboard.png
```

## Optional files

- `helpers.yaml` for dashboard-specific helpers that are required to make the dashboard work
- `scripts.yaml` for dashboard-referenced scripts that should be included with the package

## Rules for all published dashboards

1. Keep top-of-file header comments in `dashboard.yaml`.
2. Keep each dashboard README current.
3. Remove or redact sensitive information.
4. Replace sensitive values with `!secret` (private use) or neutral placeholders for public sharing.
5. Sanitize entity names and IDs if they reveal private details (for example station/account/device identifiers).

## Current packages

- `control/`
- `lighting/`
- `network/`
- `security/`
- `severe_weather/`
- `severe_weather_v1/`
- `sports_tracker/`
- `weather/`

## Package-specific notes

- `severe_weather/` (current) includes two full-width line gauges under the semicircle gauge grid
  (Rain Intensity + Wind Gust) using `custom:entity-progress-card-template`.
- `severe_weather/` also includes side-by-side live exterior camera cards (front door left, backyard right)
  using `picture-entity` cards.

Use `_template/` as a starting point for new dashboard packages.
