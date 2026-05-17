# Herons Hub Design System
Version: 1.1.0  
Last updated: 2026-05-16

This document defines the production branding and layout rules for Herons Hub.  
It is based on the UMak brand guideline reference and adapted to this app architecture.

## 1) Brand Identity
- Tone: academic, modern, focused, community-first
- Visual balance: high-contrast dark navigation + light content surfaces
- Corner style: rounded cards and pill controls for friendly readability
- UI behavior: quick scan, low visual noise, predictable interaction patterns

## 2) Typeface System
Two font families are mandatory across the app:

1. Marcellus SC (display and formal headings)
2. Metropolis (UI, body, controls, metadata)

Fallbacks:
- Marcellus SC -> `Georgia, serif`
- Metropolis -> `Inter, system-ui, sans-serif`

## 3) Typography Scale
Use these sizes and weights for consistent hierarchy.

| Token | Family | Size | Weight | Line Height | Usage |
|---|---|---:|---:|---:|---|
| Display L | Marcellus SC | 48px | 400 | 1.1 | Hero titles |
| Display M | Marcellus SC | 36px | 400 | 1.15 | Page hero subtitles |
| Heading L | Marcellus SC | 28px | 400 | 1.2 | Primary section titles |
| Heading M | Marcellus SC | 20px | 400 | 1.25 | Secondary section titles |
| Label L | Metropolis | 16px | 700 | 1.3 | Strong inline labels |
| Label M | Metropolis | 14px | 700 | 1.3 | Buttons, nav actions |
| Body M | Metropolis | 14px | 500 | 1.45 | Standard body text |
| Body S | Metropolis | 12px | 500 | 1.45 | Helper and metadata |
| Caption | Metropolis | 11px | 600 | 1.35 | Minor status text |

## 4) Color System
Core production colors:

- Brand navy: `#111c4e`
- Active blue: `#1d4ed8`
- Neutral black: `#111111`
- Surface white: `#ffffff`
- Soft panel bg: `#f4f6f8`
- Border neutral: `rgba(17, 17, 17, 0.24)`

Status colors (alerts only):
- Success: `#1a7a4a`
- Warning: `#b8860b`
- Error: `#c0392b`

## 4.1) Contrast Standards (Font vs Background)
Accessibility target:

- Body and control text: minimum `4.5:1`
- Large text (`>=24px` regular or `>=19px` bold): minimum `3:1`
- Critical actions, nav, badges: prefer `>=7:1` where possible

Approved text/background pairs:

| Use Case | Text | Background | Contrast |
|---|---|---|---:|
| Default body text | `#111111` | `#ffffff` | 18.88:1 |
| Body text on app surface | `#111111` | `#f4f6f8` | 17.43:1 |
| Primary nav text | `#ffffff` | `#111c4e` | 16.15:1 |
| Active filter chip text | `#ffffff` | `#1d4ed8` | 6.70:1 |
| Footer contact heading | `#334155` | `#e5e7eb` | 8.36:1 |
| Footer contact link | `#001035` | `#e5e7eb` | 15.07:1 |

Disallowed pair in UI controls:

- `#111111` text on `#1d4ed8` background (`2.82:1`) -> fails body-text contrast.

## 5) Filter Chip Standard
Dashboard filter tags use a strict two-color interaction rule:

- Idle: white background + black text/border
- Active: blue background + white text
- Hover: black border increases contrast

No category-specific chip colors are used in the filter row.

### Filter row structure
- Section title: Metropolis, 17px, weight 700, uppercase
- Section body: Metropolis, 12px, weight 500
- Chip height: 34px
- Chip radius: full (9999px)
- Chip text: Metropolis, 13px, weight 700

Sidebar card emphasis:
- Trending item title: Metropolis, bold (700)
- Upcoming event title: Metropolis, bold (700)

## 6) Layout and Spacing
Dashboard spacing rhythm:

- Shell horizontal padding: 20px desktop, 8px mobile
- Major section gap: 24px
- Card spacing: 10px to 16px
- Filter title to body spacing: 4px
- Filter meta to chips spacing: 8px

Responsive breakpoints:

- Mobile: `<= 768px`
- Tablet: `769px - 1320px`
- Desktop: `> 1320px`

## 7) Component Rules
- Buttons: Metropolis 700 for primary actions, minimum height 38px
- Cards: white/light surface, subtle border, restrained shadow
- Metadata: never heavier than 600 weight
- Body copy: always Metropolis
- Display/section titles: Marcellus SC only

## 8) Current Implementation Map
Primary files aligned with this document:

- `flask_backend/app/templates/dashboard.html`
- `flask_backend/app/static/css/dashboard.css`
- `flask_backend/app/templates/base.html`

## 9) Governance
When adding or revising UI:

1. Keep Marcellus SC only for display and formal headings.
2. Keep Metropolis for interactive controls and body content.
3. Preserve two-color filter chip behavior.
4. Do not introduce new accent colors without updating this spec.
