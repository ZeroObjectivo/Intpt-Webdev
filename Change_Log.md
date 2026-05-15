# Herons' Hub Community Platform - Update Log
**Date:** May 14, 2026

This document summarizes the recent major updates, bug fixes, and feature implementations for the Herons' Hub platform.

---

## [Unreleased] - 2026-05-16

### Added
- **Synced Skeleton Loading:** Implemented a high-fidelity skeleton loading state that matches the count and structure of the actual posts. The skeleton now dynamically reflects the presence of attachments (images) and uses a refined shimmer animation for a more polished "Facebook-like" experience. (References: `flask_backend/app/templates/dashboard.html`, `flask_backend/app/static/css/dashboard.css`, `flask_backend/app/static/js/realtime_sync.js`)
- **Infinite Scrolling with Skeleton:** Implemented efficient infinite scrolling for the dashboard feed using the Intersection Observer API. New posts are fetched on-demand as the user scrolls, with dedicated infinite scroll skeletons displayed during retrieval. This improves initial load performance and memory efficiency. (References: `flask_backend/app/routes/core.py`, `flask_backend/app/templates/dashboard.html`, `flask_backend/app/static/js/realtime_sync.js`)

### Changed
- **Smooth Dashboard Reveal:** Integrated a smooth opacity transition for revealing the home feed content after the initial skeleton load, eliminating jarring layout jumps.

## [Unreleased] - 2026-05-14

### Added
- **Real-Time Notifications:** Implemented real-time notifications using Supabase Realtime. New notifications now appear instantly without requiring a page refresh. (References: `flask_backend/app/templates/base.html`, `flask_backend/app/__init__.py`)
- **Advanced Multi-Image Upload UI:** Implemented Facebook-style image management in the "Create Post" modal with drag-and-drop reordering, limit counters (5 images), and dynamic previews.

### Fixed
- **JWT Expiration Errors:** Fixed a critical bug causing "JWT expired" errors on protected routes by implementing an automatic token refresh mechanism. (References: `flask_backend/app/routes/auth.py`)
- **Reliable Counter Synchronization:** Fixed a bug where comment and like counters on the dashboard feed were not reliably updating when modified within the modal. (References: `flask_backend/app/static/js/modal.js`)
- **Username Casing in Modal:** Implemented a multi-layered fix for all-caps usernames in the posts modal. Added a JavaScript `toTitleCase` helper to format names correctly even if stored as uppercase in the database, and applied CSS `!important` overrides for `text-transform` and `font-family` to bypass global small-caps heading styles. (References: `flask_backend/app/static/js/modal.js`, `flask_backend/app/static/css/modal.css`)
- **Dashboard Skeleton Loading:** Fixed a CSS conflict that caused the loading skeleton to remain visible even after content loaded. Redesigned the skeleton to match the new minimalist post cards and improved the reveal/hide logic in `realtime_sync.js`. (References: `flask_backend/app/static/css/dashboard.css`, `flask_backend/app/templates/dashboard.html`)

### 1. UI/UX & Design Overhaul
#### Added
- **Minimalist Modern Modal:** Completely redesigned the post modal with a focus on extreme clarity, generous white space, and a soft "Museum Gallery" atmosphere. Features elegant 24px rounding, soft layered shadows, and discreet intuitive controls.
- **Facebook-style Image Grid:** Implemented a robust multi-image grid system for post cards (1-5+ images) across both the Dashboard and Profile Timeline. Features optimized static layouts (side-by-side, featured left, 2x2 grid) with high-quality aspect ratio management.
- **Refined Comment UI:** Refactored comment and reply rendering with clean typography, soft card-like backgrounds, and improved conversational spacing.

#### Changed
- **Architectural Shift:** Moved away from trendy "vibe-coded" design patterns in favor of a more original, high-end minimalist aesthetic that prioritizes content and readability.
- **Improved Image Sizing:** Standardized image sizing for single and multiple uploads, using `object-fit: cover` and variable height caps (520px) to ensure a balanced feed experience.

### 2. Interaction Logic & Data Optimization
#### Fixed
- **Like Button UI Sync:** Fixed issues where Like status was not correctly reflected across different dashboard sections.
- **Accurate Comment Counting:** Standardized comment counting to only include top-level entries, matching user expectations.
- **Stale Modal Data:** Implemented live synchronization between the dashboard state and the open modal to ensure interaction counts are always current.

### 3. Administration & Security
#### Added
- **Unified Admin Notifications:** Integrated the modern floating flash message system into the Admin Hub.
- **Enhanced Moderation Workflow:** Integrated the new minimalist modal into the moderation feed with admin-specific flagging and warning controls.

---
**Technical Note:** New migration files have been added to the `supabase/migrations/` directory to support real-time notifications and interaction triggers. Ensure they are applied to the Supabase instance to enable full functionality.
