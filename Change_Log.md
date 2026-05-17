# Herons' Hub Community Platform - Update Log
**Date:** May 17, 2026

This document summarizes the recent major updates, bug fixes, and feature implementations for the Herons' Hub platform.

---

## [Unreleased] - 2026-05-17

### Added
- **Multi-Step Onboarding Flow:** Enhanced the registration process with a new two-step flow:
    1.  **Community Guidelines:** Improved T&C presentation with mandatory scroll-to-read validation.
    2.  **Profile Setup:** New form to collect required academic info (College, Course, Year Level) and optional details (Bio, Contact, Social Links) before users access the dashboard.
- **Dynamic Academic Selection:** Integrated real-time database-driven College and Institute selection into the onboarding process.
- **Onboarding Social Links:** Integrated a simplified version of the social links editor into the onboarding flow for new users.
- **Admin Moderation Actions:** Added "Flag Post" button and logic to `content_manage.html` and `reports_queue.html` to support explicit flagging of content for further review.
- **Shared Post Management JS:** Moved `togglePostMenu`, `showEditForm`, `hideEditForm`, `confirmDeletePost`, and `reportPost` to `main.js` to ensure consistent behavior across Dashboard and Profile pages.
- **Event Approval Workflow:** Updated post creation logic to require explicit admin approval for all "Events" category posts, ensuring calendar quality and coordination. (References: `flask_backend/app/routes/core.py`)
- **Event Calendar UI & Validation:** Redesigned the event creation form with a modern, icon-rich interface. Implemented client-side validation to disable past dates and ensure the end date is always after the start date. (References: `flask_backend/app/templates/dashboard.html`)
- **Clickable Notifications:** Integrated deep-linking into the notification system. Clicking on notifications for post approvals, likes, or comments now automatically opens the relevant post modal, fetching the data dynamically if it is not already loaded in the feed. (References: `flask_backend/app/routes/core.py`, `flask_backend/app/templates/includes/navbar.html`)
- **Notification Management:** Enhanced the notification UI with visual distinction for unread items (bold text) and implemented **Optimistic UI** for instant interaction feedback. Added "Mark all as read" and "Clear All" functionality with built-in protection against "ghost" notifications reappearing after a clear action. (References: `flask_backend/app/routes/core.py`, `flask_backend/app/templates/includes/navbar.html`)
- **Admin Moderation Refactor:** Integrated the post approval system into the general content management dashboard. Streamlined the workflow with high-visibility category pills and a dedicated **"Pending Posts" action button** featuring a real-time numerical indicator for items awaiting review. Consolidated chronological sorting into a standalone dropdown, removing redundant navigation pages. (References: `flask_backend/app/routes/admin.py`, `flask_backend/app/templates/admin/content_manage.html`)
- **Global Admin Search:** Implemented a comprehensive search bar in the Admin Hub top navigation.
    - **Universal Entity Search:** Added real-time search support for **Profiles, Posts, Reports, Verification Disputes, Scholarships, UMak Coop items, Colleges/Institutes, and System Logs.**
    - **Polished Search UI:** Redesigned the search dropdown with generous padding, improved typography, and better spacing to ensure high readability.
    - **Smart Filtering:** Extended all relevant admin routes to support deep-linked filtering via search queries for immediate navigation to filtered views. (References: `flask_backend/app/routes/admin.py`, `flask_backend/app/templates/admin/admin_base.html`)
- **Dynamic Course Dropdowns:** Refactored the "Edit Profile" and "Onboarding" sections to improve data integrity.
    - Replaced the free-text "Course" input with a dynamic dropdown in both Profile Settings and Onboarding flow.
    - Implemented real-time dependency: Course options now automatically filter based on the selected College/Institute.
    - Added `/api/courses` backend endpoint for high-performance course retrieval.
    - Populated the `courses` database table with over 60 verified UMak programs across all colleges. (References: `flask_backend/app/routes/core.py`, `flask_backend/app/templates/profile_settings.html`, `flask_backend/app/templates/onboarding.html`, `flask_backend/setup_courses.py`)
- **UMak Coop Catalog Overhaul:**
    - **Advanced Search & Filtering:** Added a real-time search bar and multi-dimensional filters (Category, Availability, Sorting) for both students and admins.
    - **Smart Categorization:** Introduced standardized categories: **Books, Uniforms, Patches, and ID Laces**.
    - **Admin Moderation Tools:**
        - Refined the item creation flow with mandatory category selection and price validation (> 0).
        - Optimized the management grid with high-density item cards for easier bulk review.
        - Integrated backend filtering for large catalog management.
    - **UI/UX Polishing:** Improved visual hierarchy with category pills, availability indicators, and better price labels. (References: `flask_backend/app/routes/admin.py`, `flask_backend/app/routes/core.py`, `flask_backend/app/templates/umak_coop.html`, `flask_backend/app/templates/admin/catalog_manage.html`)
- **User Management UX Improvements:**
    - **Real-time Directory Search:** Implemented live, debounce-powered search in the Full User Directory for instant profile discovery without page reloads.
    - **Dynamic Activity Status:** Replaced static status text with live activity indicators. Users now show "Online" with a glowing green dot if active within 5 minutes, or "Offline" with a "time ago" relative timestamp (e.g., "3h ago").
    - **Heartbeat Middleware:** Added a throttled backend hook that securely updates user activity timestamps every 2 minutes during active sessions.
    - **Collapsible Warnings:** Unified the User Management interface by making the Warning History section collapsible, matching the Recent Posts and Comments sections. (References: `flask_backend/app/routes/admin.py`, `flask_backend/app/templates/admin/users.html`, `flask_backend/app/templates/admin/user_manage.html`, `flask_backend/app/__init__.py`)
- **Notification Display Fixes:** 
    - Removed numerical notification count indicators from desktop, mobile, and admin interfaces, replacing them with a cleaner "New" label or a simple red dot. (References: `flask_backend/app/templates/includes/navbar.html`, `flask_backend/app/templates/admin/admin_base.html`)
    - **Complete Notification UI Re-Implementation:** To permanently fix a persistent styling glitch, the entire notification bell and dropdown component was removed and re-implemented from scratch.
        - **Isolated Component:** The new system uses unique, specific CSS class names (e.g., `.notif-item`) and self-contained styles, making it completely immune to conflicting global styles from `dashboard.css` or other stylesheets.
        - **Restored Server-Side Rendering:** The fast and reliable initial render from the server has been restored, eliminating the "pop-in" effect from the previous workaround.
        - This "rip and replace" approach guarantees a stable, consistent, and glitch-free notification experience on all pages. (References: `flask_backend/app/templates/includes/navbar.html`)
    - Simplified interaction notification titles by removing redundant "on your post" and "to your comment" suffixes for a more concise and readable feed. (References: `flask_backend/app/routes/core.py`)

### Changed
- **Dashboard Feed Refactor:** Refactored `dashboard.html` to use the shared `includes/post_card.html` template, reducing code duplication by ~150 lines and ensuring a unified UI.
- **Post Card UI Enhancements:** Updated `includes/post_card.html` with improved styling (rounded corners on images and overlays) to match the latest design standards.

### Fixed
- **Onboarding Completion (500 Error):** Fixed a critical 500 Internal Server Error on `/onboarding/complete` caused by a missing `flash` import in `auth.py`. 
- **Profile Saving Logic:** Corrected the onboarding flow to save social links to the dedicated `profile_social_links` table instead of the non-existent `social_links` column in the `profiles` table.
- **Metadata Safety:** Added safety checks for user metadata during onboarding to prevent crashes if metadata is missing.
- **Profile Settings Save Button:** Fixed a JavaScript typo where an undefined variable was preventing the "Save Changes" button from enabling when changes were made. (References: `flask_backend/app/templates/profile_settings.html`)
- **Admin Dashboard Layout:** Fixed a `jinja2.exceptions.UndefinedError` by removing the experimental storage analytics card and reverting related backend logic while preserving the requested user breakdown statistics.
- **Database Connection Issues:** Removed SQL-based storage size fetching which was causing DNS resolution errors on some environments.
- **Template Crash:** Fixed an `UndefinedError` in `post_card.html` caused by calling `.astimezone()` on a `None` date object when a post's creation date was missing or invalid.
- **Security Hardening Tests:** Updated `test_security_hardening.py` to match the current template design (consolidated forms) and fixed outdated assertions.
- **Mock Supabase Tests:** Fixed `test_create_post.py` by improving the `FakeSupabase` mock to support more complex queries (`in_`, `gt`, `is_`, `or_`) and correcting the patching strategy to ensure authentication tokens are correctly simulated.
- **Dashboard Layout Tests:** Updated `test_dashboard_layout.py` to match the actual template logic (using `.onclick` instead of `addEventListener`, and removing checks for removed functions like `handleMockSubmission`).

### Removed
- **Experimental Templates:** Deleted outdated `main_profile.html` and `social_profile.html` experimental files after confirming all features are integrated into the primary templates.

---

## [Unreleased] - 2026-05-16

### Added
- **Synced Skeleton Loading:** Implemented a high-fidelity skeleton loading state that matches the count and structure of the actual posts. The skeleton now dynamically reflects the presence of attachments (images) and uses a refined shimmer animation for a more polished "Facebook-like" experience. (References: `flask_backend/app/templates/dashboard.html`, `flask_backend/app/static/css/dashboard.css`, `flask_backend/app/static/js/realtime_sync.js`)
- **Infinite Scrolling with Skeleton:** Implemented efficient infinite scrolling for the dashboard feed using the Intersection Observer API. New posts are fetched on-demand as the user scrolls, with dedicated infinite scroll skeletons displayed during retrieval. This improves initial load performance and memory efficiency. (References: `flask_backend/app/routes/core.py`, `flask_backend/app/templates/dashboard.html`, `flask_backend/app/static/js/realtime_sync.js`)

### Changed
- **Smooth Dashboard Reveal:** Integrated a smooth opacity transition for revealing the home feed content after the initial skeleton load, eliminating jarring layout jumps.

## [Unreleased] - 2026-05-14

### Added
- **Bulk Moderation Tools:**
    *   Implemented batch processing in **Approvals** and **Reports** queues.
    *   Added bulk selection (checkboxes + Select All) and floating action bars.
    *   New backend routes for bulk approval, rejection, deletion, and flag dismissal.
- **Refined User Reporting:**
    *   Replaced standard prompts with uniform system modals for reporting accounts.
    *   Simplified the reporting flow to a dropdown reason without mandatory messages.
- **Unified Reporting & Moderation:**
    - Updated `reports` table to support reporting user accounts (`reported_user_id`).
    - Implemented **Account Reporting** on the user side (profile page) with a new route `/profiles/<id>/report`.
    - Consolidated "Reports Queue" and "Posts Reported" into a single, unified moderation interface.
    - Added **Type Filtering** (Posts vs Accounts) and advanced sorting to the moderation queue.
    - Updated Admin Dashboard overview to remove redundant cards and streamline navigation.
- **UI Fixes:**
    - Corrected the logo in the Admin Portal sidebar to use the standardized `Logo.png`.
- **Centralized Academic Units:**
    - Created a new database table `colleges_institutes` for managing Colleges, Schools, and Institutes.
    - Added an Admin management interface (`/admin/colleges`) to add/remove academic units.
    - Synchronized dropdowns across **Event Creation** and **Profile Settings** to use the same dynamic database list.
    - Separated "Colleges" from "Schools & Institutes" in all dropdowns for better organization.
- **Admin Dashboard Enhancements:**
    - Implemented dynamic **User Breakdown** statistics by college and course in `flask_backend/app/routes/admin.py`.
    - Updated `flask_backend/app/templates/admin/dashboard.html` to display live student distribution data instead of placeholders.
- **System Audit Logs:**
    - Created a new **System Logs** page (`flask_backend/app/templates/admin/logs.html`) to view a comprehensive audit trail of administrative actions.
    - Added a new route `/admin/logs` in `flask_backend/app/routes/admin.py` with search and action filtering capabilities.
    - Integrated the logs page into the admin sidebar in `flask_backend/app/templates/admin/admin_base.html`.
- **Real-Time Notifications:**
 Implemented real-time notifications using Supabase Realtime. New notifications now appear instantly without requiring a page refresh. The system pushes updates to the client, which dynamically updates the notification count and prepends the new notification to the dropdown list. A toast message is also displayed to the user. (References: `flask_backend/app/templates/base.html`, `flask_backend/app/__init__.py`, `flask_backend/app/templates/includes/navbar.html`)
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
