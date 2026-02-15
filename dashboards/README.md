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

## Rules for all published dashboards

1. Keep top-of-file header comments in `dashboard.yaml`.
2. Keep each dashboard README current.
3. Remove or redact sensitive information.
4. Replace sensitive values with `!secret` (private use) or neutral placeholders for public sharing.
5. Sanitize entity names and IDs if they reveal private details (for example station/account/device identifiers).

## Current packages

- `severe_weather/`
- `severe_weather_v1/`

Use `_template/` as a starting point for new dashboard packages.
