# Herons Hub: UI/UX Design System & Reference
**Version:** 1.0.0
**Context:** Frontend design tokens, component guidelines, and CSS/Tailwind referencing for the Herons Hub Community Platform.

---

## 1. Core Brand Identity
The UI strictly enforces the official University of Makati visual identity, modernized for a SaaS-like community platform.

* **Brand Vibe:** Academic, Innovative, Exclusive, Community-oriented.
* **Layout Philosophy:** Mobile-first, responsive, utilizing clean spacing and subtle glassmorphism for layered modals.
* **Border Radius:** Global radius is `0.5rem` (8px) for cards and buttons to maintain a friendly but structured look.

---

## 2. Color Palette & Tokens
Use these exact hex codes for CSS variables or Tailwind configuration.

### Primary Blue (Space Cadet)
Used for primary backgrounds, navbars, active states, and strong contrasts.
* `blue-900` / `--color-primary-darkest`: **#01061c** (Deep background / Dark Mode)
* `blue-800` / `--color-primary-dark`: **#060e33**
* `blue-500` / `--color-primary-base`: **#28336b** (Main Brand Blue / Headers)
* `blue-300` / `--color-primary-light`: **#47528a** ### Primary Gold (Maximum Yellow)
Used for primary calls-to-action (CTAs), highlights, and warning states.
* `gold-900` / `--color-accent-darkest`: **#aca404**
* `gold-800` / `--color-accent-dark`: **#ddd311**
* `gold-500` / `--color-accent-base`: **#fef760** (Primary Buttons)
* `gold-300` / `--color-accent-light`: **#fff989**

### Secondary Blue (Silver Lake Blue)
Used for hover states, secondary backgrounds, and lighter UI elements.
* `silver-900` / `--color-secondary-darkest`: **#275996**
* `silver-800` / `--color-secondary-dark`: **#406fa5**
* `silver-500` / `--color-secondary-base`: **#8bb0dc**
* `silver-300` / `--color-secondary-light`: **#c0d5f0** (Card Hover States / Subtle Backgrounds)

### Neutral & Backgrounds
* `bg-main`: **#f4f6f8** (App background)
* `bg-surface`: **#ffffff** (Cards, Sidebars, Post containers)
* `text-main`: **#1a1d20** (Standard body text)
* `text-muted`: **#6c757d** (Timestamps, secondary info)

---

## 3. Typography Hierarchy
The dual-font strategy separates academic authority from modern usability.

### Headings (Marcellus - Serif)
Used *only* for page titles, large banners, and formal sections.
* **Font-Family:** `'Marcellus', serif`
* **Weights:** 400 (Regular)
* **Usage Example:** `h1` Platform Title, `h2` Section Headers ("Heron Business Marketplace").

### UI & Body (Metropolis - Sans-Serif)
Used for all interface elements, navigation, buttons, and user-generated content.
* **Font-Family:** `'Metropolis', sans-serif` (Fallback: `'Inter', sans-serif`)
* **Weights:** 400 (Regular), 600 (Semi-Bold), 700 (Bold)
* **Usage Example:** Post body text, `<UserNav />`, Timestamps, Tags.

---

## 4. Component Guidelines

### Buttons
* **Primary (Action):** Background `#fef760` (Gold Base), Text `#01061c` (Dark Blue), Bold. Subtle hover lift (`translate-y-[-1px]`).
* **Secondary:** Background `#c0d5f0` (Light Silver Lake), Text `#28336b`.
* **Danger/Destructive:** Background `#ef4444` (Standard Red fallback), Text White. 

### Cards & Surfaces
* **Background:** Solid White (`#ffffff`).
* **Border:** 1px solid `#e2e8f0` (Light gray) or borderless with shadow.
* **Shadow (Light):** `0 2px 4px rgba(1, 6, 28, 0.05)` — Use for static feed posts.
* **Shadow (Hover):** `0 4px 12px rgba(1, 6, 28, 0.1)` — Use for interactive cards (COOP Store, Scholarships).

### Tags & Badges
* **Style:** Pill shape (`border-radius: 9999px`), small text (`0.75rem`), Semi-bold.
* **Lost & Found:** Soft Red/Orange background, Dark Red text.
* **Heron Business:** Soft Green background, Dark Green text.
* **Question:** Soft Silver Lake Blue background, Space Cadet text.

---

## 5. Layout & Responsive Structure

### Mobile-First Breakpoints
* **Mobile (Default):** 0px - 767px. (Bottom tab navigation, single column feed).
* **Tablet (md):** 768px - 1023px. (Left sidebar appears, main feed scales).
* **Desktop (lg):** 1024px+. (3-column layout: Left Nav, Center Feed, Right Context Widget).

### Glassmorphism Effects (Modals & Auth)
For the gated entry screen and pop-up modals, utilize modern glass aesthetics to maintain depth.
* **Backdrop Blur:** `backdrop-filter: blur(12px)`
* **Overlay Color:** `rgba(1, 6, 28, 0.6)` (Space Cadet with 60% opacity)
* **Modal Surface:** White background with a subtle inner border (`border: 1px solid rgba(255,255,255,0.2)`).

---

## 6. Iconography
* **Library:** Lucide Icons / Phosphor Icons.
* **Stroke Width:** 1.5px to 2px for clean, scalable vector graphics.
* **Sizing:** `20x20` for inline text, `24x24` for navigation tabs.