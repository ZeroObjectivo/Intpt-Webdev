# Project Change Log
**Current Date:** May 12, 2026

This document summarizes the recent major updates, bug fixes, and feature implementations for the Herons' Hub platform.

---

## [Unreleased] - 2026-05-12

### 1. Merge Conflict Resolution & Layout Consolidation
*   **Resolved Dashboard Conflicts:** Fixed critical merge markers (`<<<<<<< HEAD`) in `dashboard.html`.
*   **Layout Consolidation:** Unified the dashboard structure, removing redundant code blocks while preserving the primary sidebar and feed column.
*   **HTML Structural Fixes:** Corrected missing closing `div` tags and indentation issues for better stability.

### 2. Dynamic Post Features
*   **Category-Specific Metadata:** Added support for `Price`, `Location`, `Status`, and `Event Date` fields.
*   **Smart Post Creation Modal:** 
    *   Implemented interactive JavaScript to show/hide fields based on the selected category.
    *   Added dynamic status options (e.g., "Available/Sold" for Marketplace vs. "Lost/Found" for Lost & Found).
*   **Backend Persistence:** Updated Flask `create_post` route to sanitize and save new dynamic fields to Supabase.

### 3. Category Filtering Functionality
*   **Server-Side Filtering:** Modified the `/dashboard` route to accept a `category` query parameter.
*   **Supabase Integration:** Updated data fetching logic to filter posts by category when requested.
*   **Interactive Navigation:** Converted UI pills into active links that trigger the filtering logic.

### 4. UI/UX Polishing & Aesthetics
*   **Modern Styling:** Increased global border radius to `16px` for smoother post cards and containers.
*   **Centered Alignment:** Used flexbox to fix vertical text alignment in category pills.
*   **Category Color Coding:** 
    *   Established a unified color palette for all 5 categories.
    *   Applied consistent color themes to both filter pills and post badges for better visual hierarchy.

---

## Technical File Changes
- `flask_backend/app/templates/dashboard.html`: Major refactor and UI updates.
- `flask_backend/app/routes/core.py`: Backend filtering and post creation logic.
- `flask_backend/app/static/css/dashboard.css`: UI/UX enhancements and color coding.
- `CHANGELOG.md`: Project-wide tracking.
- `Md/Changelog_DynamicFields.md`: Feature-specific documentation.
