# Project Change Log
**Current Date:** May 12, 2026

This document summarizes the recent major updates, bug fixes, and feature implementations for the Herons' Hub platform.

---

## [Unreleased] - 2026-05-12

### 1. Merge Conflict Resolution & Layout Consolidation
### Fixed
- **Date Parsing Error:** Updated `datetime_obj` Jinja2 filter to handle variable-precision Supabase timestamps (with and without microseconds), resolving 500 errors on the dashboard.
- **TemplateAssertionError:** Registered missing `datetime_obj` Jinja2 filter and `now` context processor in the Flask app factory to support relative timestamp calculations.
- **Dashboard Conflicts:** Fixed critical merge markers (`<<<<<<< HEAD`) in `dashboard.html`.
- **Layout Consolidation:** Unified the dashboard structure, removing redundant code blocks while preserving the primary sidebar and feed column.
- **HTML Structural Fixes:** Corrected missing closing `div` tags and indentation issues for better stability.

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

### 5. Inline Post Creation & Multi-Image Support
*   **Facebook-Style Share Box:** Replaced the modal-based post creation with an expandable inline input area.
*   **Auto-Expanding UI:** The post input now expands on focus/typing, revealing category and dynamic field options.
*   **Cumulative Multi-Image Upload:** 
    *   Supports batch selection of up to 5 images.
    *   Images can be added cumulatively, and individual images can be removed before posting.
    *   Real-time batch grid preview allows users to manage their post images effectively.
*   **Grid Rendering:** Updated post rendering to display multiple images in a responsive, Facebook-style grid layout.
*   **Backend Image Handling:** Updated the Flask backend to process batch multipart form data, store images in Supabase, and persist an array of image URLs (`image_urls`) to the database.

### 6. Database & Storage Infrastructure
*   **Comprehensive Migration:** Created `supabase/migrations/20260512080000_support_multiple_images.sql` to transition from single `image_url` to `image_urls` (text array).
*   **Automated Storage Setup:** Added SQL script to automatically create the `post-images` bucket and configure RLS policies for public viewing and authenticated uploads.
*   **Interaction Schema:** Implemented `likes` (Helpful) and `comments` tables with full Row Level Security (RLS) and cascading deletes.
*   **Schema Hardening:** Ensured all dynamic post columns (`price`, `location`, `status`, `event_date`) are present and documented with SQL comments.

### 7. UI & UX Refinements
*   **Relative Timestamps:** Implemented dynamic relative time display (e.g., "5m", "2h", "1d") for posts, with a hover-over tooltip showing the exact full date and time.
*   **Inline Share Box:** Replaced the modal-based post creation with an expandable inline input area.
*   **Cumulative Multi-Image Upload:** Supports batch selection of up to 5 images, with real-time preview and individual removal.
*   **Grid Rendering:** Updated post rendering to display multiple images in a responsive, Facebook-style grid layout.

---

## Technical File Changes
- `flask_backend/app/templates/dashboard.html`: Updated timestamp logic, inline share box, and image grid.
- `flask_backend/app/routes/core.py`: Backend filtering and post creation logic.
- `flask_backend/app/static/css/dashboard.css`: UI/UX enhancements and grid styles.
- `supabase/migrations/20260512080000_support_multiple_images.sql`: Migration for multi-image column support.
- `CHANGELOG.md`: Project-wide tracking.
- `Md/Changelog_DynamicFields.md`: Feature-specific documentation.
