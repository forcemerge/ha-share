# Frontend Resources (`www`)

This folder contains shareable frontend assets (custom cards, scripts, and UI helpers).

## Included

- `notion-travel-trip-card.js` - custom Lovelace card for Notion Travel mission console / timeline UX.

## Usage

1. Copy the JS file to your Home Assistant `/config/www/` folder.
2. Add it as a Lovelace resource:
   - URL: `/local/notion-travel-trip-card.js`
   - Type: `module`
3. Use card type `custom:notion-travel-trip-card`.
