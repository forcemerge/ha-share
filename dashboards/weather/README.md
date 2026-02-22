# Weather

Sanitized Weather dashboard package for live station telemetry, history graphs, and optional embedded station UI.

## Files

- `dashboard.yaml` - sanitized dashboard definition
- `helpers.yaml` - optional Grass Guru helper entities
- `scripts.yaml` - optional Grass Guru + Notion script references
- `images/dashboard.png` - add one screenshot here

## Requirements

- Weather station entities for temperature, wind, precipitation, UV, and station health
- `custom:windrose-card`
- Secret URL value for `weather_station_url`
- Optional OpenAI conversation agent (`conversation.openai_conversation`) for Lawn Guru scripts
- Optional Notion REST commands and secrets if using Notion upsert scripts

## Sanitization notes

This package replaces station-specific entity IDs and location references with neutral `local_weather_*` placeholders.

Update entity IDs and secret values to match your weather integration.

The Lawn Guru tab references `grass_guru_*` helpers and scripts. Merge `helpers.yaml` / `scripts.yaml`
if you want that functionality; otherwise remove the Lawn Guru view from `dashboard.yaml`.

## Screenshot

Place your screenshot at:

- `images/dashboard.png`

![Dashboard screenshot](images/dashboard.png)
