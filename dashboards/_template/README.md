# Dashboard Template

Briefly describe what this dashboard does and who it is for.

## Files

- `dashboard.yaml` - sanitized dashboard definition
- `helpers.yaml` - optional helpers needed by this dashboard
- `scripts.yaml` - optional scripts referenced by this dashboard
- `images/dashboard.png` - expected screenshot image

## Requirements

List required integrations, custom cards, and helper dependencies.

## Sanitization notes

- Sensitive identifiers have been redacted or generalized.
- Any value that should remain private is represented with `!secret` or a placeholder.

## Installation notes

1. Copy `dashboard.yaml` to your HA dashboards path.
2. Add/merge helper definitions from `helpers.yaml` if present.
3. Add/merge scripts from `scripts.yaml` if present.
4. Update entities/secrets to match your environment.

## Screenshot

![Dashboard screenshot](images/dashboard.png)
