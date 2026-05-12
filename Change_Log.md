# Herons' Hub Community Platform - Update Log
**Date:** May 13, 2026

This document summarizes the recent major updates, bug fixes, and feature implementations for the Herons' Hub platform.

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

### Changed
- **Image Interactions:** Removed hover effects (scaling and brightness filters) from post images to maintain a cleaner, static appearance in the feed.
- **Single-Image Layout:** Limited the maximum height of single-image posts to 400px, preventing cards from expanding excessively and improving feed readability.
- **Marketplace UX:** Removed the "Sold" status option from the post creation modal. "Sold" is now reserved for post updates rather than initial creation.
- **Dashboard Backend:** Updated `load_dashboard_data` to fetch trending posts and user profiles in a single pass.
- **UI Alignment:** Fixed the alignment of post image grids and badges in the dashboard.

---
**Technical Note:** New migration files have been added to the `supabase/migrations/` directory. Ensure they are applied to the Supabase instance to enable the new database fields, reporting table, and RPC functions.
