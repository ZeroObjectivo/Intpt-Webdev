# Herons' Hub Community Platform - Update Log
**Date:** May 14, 2026

This document summarizes the recent major updates, bug fixes, and feature implementations for the Herons' Hub platform.

---

## [Unreleased] - 2026-05-14

### 1. Front-end Integration & Image Enhancements
### Added
- **Multiple Image Support:** Refactored post creation and display to support up to 5 images per post.
- **Dynamic Image Grid:** Implemented a Facebook-style responsive grid (`fb-grid`) that adjusts layouts based on the number of images (1-5).
- **Advanced Multi-Image Upload UI:** Implemented Facebook-style image management in the "Create Post" modal.
    - Additive image selection (new selections append to current list).
    - Drag-and-drop reordering of selected images.
    - Individual image deletion from the preview grid.
    - Dynamic "Add More" button within the preview container.
    - Improved preview performance using `URL.createObjectURL`.
    - Automatic synchronization of custom file order with the form submission using the `DataTransfer` API.
- **Enhanced Post Creation Validation:** The "Post" button now dynamically enables/disables based on content or image presence, and validates category-specific required fields.
- **Timezone Support:** Added `tzdata` dependency to handle Asia/Manila timezone correctly on Windows environments.

### Changed
- **Branch Merge:** Merged `frontend` branch into `main`. This integration brings in all the latest UI components, admin dashboard features, and profile settings while preserving all existing backend features on `main`.
- **CSS Assets:** Rebuilt `flask_backend/app/static/css/style.css` using Tailwind CSS to ensure full synchronization between the merged templates and the generated styles.

### Fixed
- **Single Image Post Sizing:** Optimized the display for single-image posts to prevent cropping while capping the height at 550px. Images are now contained within a soft-slate background, matching Facebook's behavioral patterns for mixed aspect ratios.
- **Image Interaction Polish:** Removed the unwanted zoom effect when hovering over post images in the feed for a cleaner, more professional look.
- **Modal Trigger Logic:** Fixed a bug where clicking on single-image posts failed to open the image gallery modal due to an incorrect conditional check in the template.
- **Post Card Image Grid Stacking:** Fixed an issue where post images would stack vertically by moving `fb-grid` styles to a dedicated `dashboard.css` file and ensuring high CSS specificity.
- **Post Card Image Sizing:** Resolved issues where single post images would "overreact" to the card size by enforcing a `max-height: 500px` and unified object-fit behavior.
- **Unified Image Rendering:** Refactored `dashboard.html` and `profile_settings.html` to use a consistent `fb-grid` system for both legacy `image_url` and new `image_urls` fields.

### Changed
- **Facebook-Style Grid Refinements:** Enhanced the `fb-grid` CSS in `input.css` with smoother transitions, hover effects, and more robust grid templates for 1-5 images.
- **Image Modal Integration:** Synchronized single-image clicks to open the appropriate modal context (comment modal vs. image gallery) based on the image source.

---

## [Unreleased] - 2026-05-13

### 1. Like and Comment Functionality
### Added
- **Comment Reply Functionality:**
    - Implemented threaded comment support by adding a `parent_id` column to the `comments` table.
    - Updated `add_comment` backend route to handle optional `parent_id`.
    - Added "Reply" functionality in the modal: clicking "Reply" auto-populates the mention and shows a "Replying to" indicator.
    - Implemented UI for canceling replies and clearing mention state.
- **Backend Likes & Comments Logic:**
    - Implemented `toggle_like` route to handle post likes with optimistic UI updates.
    - Implemented `get_comments` and `add_comment` routes to fetch and persist user comments.
    - Created RPC functions (`increment_likes_count`, `decrement_likes_count`, `increment_comments_count`, `decrement_comments_count`) to handle atomic counter updates in the database.
- **Database Schema Updates:**
    - Added `comments_count` column to the `posts` table via migration.
    - Initialized existing counts based on existing data in `likes` and `comments` tables.
- **Interactive Modal Enhancements:**
    - **Comment Modal:** Enabled opening the modal via the "Comment" button on post cards, even for text-only posts.
    - **Dynamic Comments Section:** Implemented real-time comment fetching and rendering within the modal side panel.
    - **Comment Submission:** Added an inline comment form in the modal with immediate UI feedback and dashboard counter synchronization.
- **Optimistic UI Updates:** 
    - Implemented optimistic like toggling on post cards for a snappier user experience.
    - Synced like status and counts between the dashboard feed and the open modal.

### 2. Post Creation & Community Enhancements
### Added
- **Admin Dashboard Features:**
    - Implemented a comprehensive Admin Dashboard with real-time statistics for users, posts, reports, and recent activities.
    - **User Management:** Created a full directory view with search and filtering capabilities. Added detailed user management pages to view profiles, activity history (posts), and sanctions (warnings).
    - **Content Moderation:** Implemented category-specific content management views to review and moderate all posts.
    - **Verification Disputes:** Added a system for admins to manage login verification disputes from students.
    - **Admin Logs & Warnings:** Implemented backend tracking for admin actions and a warning system for users.
    - **Database Migration:** Added a new migration (`20260513000600_admin_features.sql`) to support `admin_logs`, `verification_disputes`, `warnings`, and enhanced `profiles` fields.
    - **UI/UX Updates:** Enhanced the Admin Hub sidebar and dashboard with dynamic links and interactive elements.
- **Profile Settings Page:**
    - Created a dedicated settings area for users to manage their academic and contact information.
    - Fields include: College (dropdown), Course, Year Level, Bio, and Contact Number.
    - Implemented **Contact Privacy:** Users can toggle between "Public" and "Only Me" for their contact number visibility.
    - Locked identity fields (Name and Profile Picture) to ensure sync with verified Google UMak accounts.
    - Designed a unified, mobile-responsive UI with consistent Herons' Hub branding.
- **Custom Confirmation Modal:**
    - Replaced native browser `confirm()` dialogs with a custom, themed system modal for all delete actions (posts and comments).
    - Designed with a "soft-red" theme to provide clear visual warning while matching the project's aesthetic.
    - Implemented a reusable `showConfirmModal` system with callback support for snapping actions.
- **Post & Comment CRUD:**
    - Implemented full Edit and Delete functionality for users to manage their own content.
    - Added backend routes (`update_post`, `delete_post`, `update_comment`, `delete_comment`) with author-only security checks.
    - Added a kebab menu (three dots) to post cards on the dashboard for owners.
    - Implemented inline post editing with a hidden form that preserves category context.
    - Added Edit and Delete icons to comments within the interactive modal for owners.
    - Implemented real-time dashboard counter updates when comments are deleted.
- **Rate Limiting:** Implemented a 30-second cooldown for post creation in the Flask backend to prevent spam and duplicate postings.
- **Event Duration Support:** Added `event_end_date` to the `posts` table and updated the frontend share box to support Start and End dates for events.
- **Reporting System:** Created a `reports` table with Row Level Security (RLS) to allow users to flag inappropriate content for moderation.
- **Dynamic Trending Now:** The "Trending Now" sidebar is now dynamically populated based on the `likes_count` of posts, showing the top 3 most liked items across all categories.

### Fixed
- **Naive vs Aware Datetime Error:** Resolved `TypeError: can't subtract offset-naive and offset-aware datetimes` on the dashboard by ensuring the `now` variable passed to the template is offset-naive (UTC), matching the output of the `datetime_obj` filter.
- **Modal Image Visibility:** Updated modal logic to hide the main image view when opening a post that contains no images (text-only posts).
- **Dashboard Data Loading:** Updated `load_dashboard_data` to properly fetch `likes_count`, `comments_count`, and the `user_has_liked` status for the current session.
- **Rate Limit Bug:** Prevented multiple rapid form submissions from creating duplicate database entries.
- **Template Error:** Corrected the `trending` variable passing in the `dashboard` route.
- **Storage Upload Error:** Resolved "new row violates row-level security policy" (Unauthorized) error when uploading images with posts.
- **Image Display on Cards:** Fixed issue where uploaded images were not appearing on post cards.
- **Backend Storage Authentication:** Updated `apply_supabase_auth_token` in `auth.py` to correctly propagate the user's JWT to the Supabase Storage client.
- **Profile Settings Save Button:** Fixed a bug where the "Save Changes" button in the profile settings was always grayed out due to incorrect form selection in JavaScript. Added a specific ID to the settings form to ensure correct change tracking.

### Changed
- **Image Interactions:** Removed hover effects (scaling and brightness filters) from post images to maintain a cleaner, static appearance in the feed.
- **Single-Image Layout:** Limited the maximum height of single-image posts to 400px, preventing cards from expanding excessively and improving feed readability.
- **Marketplace UX:** Removed the "Sold" status option from the post creation modal. "Sold" is now reserved for post updates rather than initial creation.
- **Dashboard Backend:** Updated `load_dashboard_data` to fetch trending posts and user profiles in a single pass.
- **UI Alignment:** Fixed the alignment of post image grids and badges in the dashboard.

---
**Technical Note:** New migration files have been added to the `supabase/migrations/` directory. Ensure they are applied to the Supabase instance to enable the new database fields, reporting table, and RPC functions.
