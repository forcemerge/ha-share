# ha-share

Public, share-focused Home Assistant repository for selected artifacts.

## Purpose

This repo publishes reusable pieces of my Home Assistant work without exposing private implementation details.

Current scope: **dashboards only**.

## What is included

- Sanitized dashboard packages under `dashboards/`
- Optional helper definitions needed by those dashboards
- Optional script definitions referenced by those dashboards
- Dashboard-specific documentation
- One screenshot PNG per dashboard (`images/dashboard.png`)

## What is not included

- Private/full Home Assistant configuration
- Secrets, tokens, API keys, hostnames, IPs, station IDs, account IDs, or other sensitive identifiers
- Environment-specific implementation details that could identify a household, location, or network

## Home Assistant setup (high-level)

- YAML-driven Home Assistant configuration managed in a private source-of-truth repository
- Dashboard and configuration enhancements developed iteratively
- In-Home-Assistant AI assistant support for day-to-day insight and operations
- MCP Server Builder tooling used for contextual exploration and safe, structured config workflows

## GitOps + AI/MCP workflow (generalized)

1. Build and validate changes in the private source-of-truth repo.
2. Use AI + MCP tooling for context gathering, verification, and implementation support.
3. Run operational guardrails (health checks, drift checks, backups, pull/deploy automation).
4. Selectively publish sanitized assets to this public repo.

This keeps production operations private while still sharing useful patterns and dashboard designs.

## Dashboard package format

Each dashboard should live in its own directory:

```text
dashboards/
  <dashboard_slug>/
    dashboard.yaml
    helpers.yaml        # optional
    scripts.yaml        # optional
    README.md
    images/
      dashboard.png     # expected single screenshot
```

## Publishing conventions

1. Keep descriptive top-of-file header comments in every `dashboard.yaml`.
2. Update README files whenever functionality or structure changes.
3. Never publish sensitive values that can be moved to secrets.
4. Sanitize/redact sensitive identifiers (including IDs embedded in entity names).

## Future scope

Potential future top-level areas:

- `automations/`
- `blueprints/`

(Added only when we start publishing those asset types.)
