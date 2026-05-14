# Herons' Hub Community Platform - Update Log
**Date:** May 14, 2026

This document summarizes the recent major updates, bug fixes, and feature implementations for the Herons' Hub platform.

---

## [Unreleased] - 2026-05-14

### 1. Interaction Logic & Data Optimization
#### Fixed
- **Like Button UI:** Fixed an issue where the Like heart would show as grayed out even if the user had already liked the post. It now correctly remains red (filled) on initial page load and in the modal.
- **Accurate Comment Counting:** Adjusted the comment counting logic to only include top-level comments in the `comments_count` field, ensuring the displayed count matches the number of comments the user sees (excluding replies by default).
- **Stale Modal Data:** Fixed a bug where opening the comment modal would show outdated like/comment counts or statuses because it was using static data from the time of page render. The modal now synchronizes with the latest live dashboard state upon opening.
- **Global Interaction Sync:** Enhanced `updateDashboardCount` and `toggleLike` in `modal.js` to ensure that likes and comment counts are synchronized across all instances of a post on the page (main feed, trending sidebar, and profile page).
- **Profile Like Check:** Fixed a backend bug in `load_profile_data` where the `user_has_liked` check was incorrectly performed against the profile owner's ID instead of the current viewer's ID.

#### Added
- **Profile Interactions:** Added Like and Comment action buttons to the post cards on the User Profile page, allowing for direct interaction from the timeline.
- **Bulk Likes Fetching:** Optimized the backend to fetch all like statuses for displayed posts in a single query, eliminating the N+1 database performance bottleneck.

### 2. Front-end Integration & Image Enhancements
### Added
- **Multiple Image Support:** Refactored post creation and display to support up to 5 images per post.
- **Dynamic Image Grid:** Implemented a Facebook-style responsive grid (`fb-grid`) that adjusts layouts based on the number of images (1-5).
- **Advanced Multi-Image Upload UI:** Implemented Facebook-style image management in the "Create Post" modal.
    - Added a dynamic **Image Limit Counter** (e.g., "1/5") that provides real-time feedback on the number of selected images and highlights in red when the maximum limit is reached.
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
- **Admin Authorization (Superadmin Access):** Fixed an issue where users with the `superadmin` role (no underscore) were unable to access the admin dashboard.
    - Updated `admin_required` decorator in `flask_backend/app/routes/admin.py` to support both `super_admin` and `superadmin` spellings.
    - Updated role-based conditional rendering in `profile_settings.html` and `admin/users.html`.
    - Updated Supabase RLS policies in `20260513000400_post_enhancements.sql` and `20260513000600_admin_features.sql` to include `superadmin` in the authorized roles list.
- **Dynamic Sidebar Features:** Fully implemented the "Trending Now" and "Upcoming Events" sidebar sections.
    - **Trending Now:** Now dynamically fetches the top 3 posts by like count. Clicking a trending topic opens the interactive comment modal for that specific post.
    - **Upcoming Events:** Now dynamically fetches the next 3 scheduled events. 
        - Implemented server-side parsing for date components (day, month) and automatic status determination (Ongoing vs. Upcoming).
        - Added `event_title` support to ensure specific event names are displayed as the primary header.
        - Ensured consistent **Asia/Manila** timezone alignment for both creation and display, fixing the previous time-mismatch issue.
- **Admin User Management NameError:** Resolved a `NameError: name 'request' is not defined` that occurred when searching for users in the admin dashboard by adding the missing `request` import from Flask in `admin.py`.
- **Interaction Counts & Spam Protection:** Fixed several issues related to post likes and comments.
    - **Spam Prevention:** Updated `toggle_like` route with a check-then-act pattern to prevent double-counting or rapid spamming from inflating like counts.
    - **Dangling Counts:** Implemented database triggers (`on_like_deleted` and `on_comment_deleted`) that automatically decrement post counters whenever a record is removed from the `likes` or `comments` tables. This ensures counts remain accurate even if a user is deleted or an admin removes content.
    - **Count Synchronization:** Added a `sync_all_post_counts` RPC function and a migration (`20260513000700_fix_interaction_counts.sql`) to recalculate and fix any existing discrepancies in the database.
- **Single Image Post Sizing:** Optimized the display for single-image posts to prevent cropping while capping the height at 550px. Images are now contained within a soft-slate background, matching Facebook's behavioral patterns for mixed aspect ratios.
- **Image Interaction Polish:** Removed the unwanted zoom effect when hovering over post images in the feed for a cleaner, more professional look.
- **Modal Trigger Logic:** Fixed a bug where clicking on single-image posts failed to open the image gallery modal due to an incorrect conditional check in the template.
- **Post Card Image Grid Stacking:** Fixed an issue where post images would stack vertically by moving `fb-grid` styles to a dedicated `dashboard.css` file and ensuring high CSS specificity.
- **Post Card Image Sizing:** Resolved issues where single post images would "overreact" to the card size by enforcing a `max-height: 500px` and unified object-fit behavior.
- **Unified Image Rendering:** Refactored `dashboard.html` and `profile_settings.html` to use a consistent `fb-grid` system for both legacy `image_url` and new `image_urls` fields.
- **Post View Background Blur:** Adjusted the post modal background to be blurred instead of black when viewing a post without images, improving visual continuity with the dashboard.
- **Unified Modal UI:** Relocated the post view close button to the top-right corner of the side panel, adopting the same circular, light-gray style as the "Create Post" modal for a more consistent user experience.
- **Reliable Counter Synchronization:** Fixed a bug where comment and like counters on the dashboard feed were not reliably updating when modified within the modal.
    - Added `data-post-id` attributes to all post cards in `dashboard.html`.
    - Refactored `updateDashboardCount` in `modal.js` to use the new ID-based selectors, ensuring immediate and accurate UI updates across both the feed and the expanded view. (References: `dashboard.html`, `modal.js`)

### 2. User Role Management
### Added
- **Redesigned Role Selection:** Replaced the simple dropdown with a click-to-edit interface in the User Management Actions page.
    - **UI/UX Improvements:** Added an "Edit" mode with radio buttons for better clarity.
    - **Confirmation Workflow:** Introduced "Save" and "Cancel" buttons to prevent accidental role changes.
    - **System Alignment:** Designed the interface to match the project's modern aesthetic using custom Tailwind classes and Alpine.js for state management.
    - **Smart Behavior:** Implemented a "click-outside" listener to automatically close the role selection when clicking elsewhere on the page.
- **Service Role Integration:** Implemented a `get_service_client` helper in the admin routes to bypass Supabase RLS policies for administrative actions.
- **Enhanced Navigation:** Added uniform "Back" buttons to all internal Admin Hub pages (User Directory, User Management, Content Moderation, Disputes, Profanity Filter) for seamless navigation.
- **Unified Notifications:** Integrated the modern floating flash message system into the Admin Hub for consistent feedback across the platform.

### 3. Profanity Filter Management
### Added
- **Dynamic Word Management:** Enabled real-time syncing of the profanity filter with the `forbidden_words` database table.
- **Add Word Functionality:** Implemented a new modal-based interface to add words to the global filter list.
- **Delete Functionality:** Added the ability to remove words from the filter with immediate database synchronization.
- **RLS Security Policies:** Created migration `20260514000100_setup_forbidden_words.sql` to ensure admins have proper SELECT/INSERT/DELETE permissions on the filter table.

### 4. Content Moderation Enhancements
### Added
- **Vertical Post Layout:** Redesigned the Content Moderation page to display posts in a vertical, single-column feed for better readability.
- **Enhanced Filtering:** Expanded the category filter to include 'Lost & Found', 'Buy & Sell', 'Question', and 'Events'.
- **Admin Post Modal:** Integrated the dashboard's post modal into the moderation hub with admin-only features.
    - **Likers List:** Admins can now see a list of users who liked a post.
    - **Post & Comment Flagging:** Added the ability to flag inappropriate posts and comments for further review.
- **Warning Workflow:** Implemented a new "Warn Author" system.
    - **Reason Selection:** Modal for selecting specific violation reasons (Inappropriate Language, Harassment, Spam, etc.).
    - **Auto-generated Messages:** Provides editable templates for warning notifications based on the selected reason.
- **Notifications System:** Created a new `notifications` database table to track system alerts and user warnings.
- **Status Tracking:** Added `is_flagged` status to both posts and comments for improved moderation tracking.

### Fixed
- **Profile Photo Visibility:** Resolved an issue where profile photos were not displaying correctly in the moderation feed.
- **Multiple Image Support:** Fixed the moderation hub to properly display and allow expansion of all attached photos in a post.
- **Content Moderation UI Fixes:**
    - **Optimized Image Sizes:** Reduced image dimensions in the moderation list (`aspect-square md:aspect-video`) and limited single-image width to improve readability.
    - **View Post Icon:** Fixed the "View Post" (eye icon) functionality by passing post IDs instead of full objects to prevent HTML attribute breakage.
    - **Admin Overlay Layout:** Resolved "messed up" layout issues by including `modal.css` in the admin view and redesigning the injected moderation controls for better fit within the theater modal.
    - **Redundancy Cleanup:** Removed unused and conflicting `adminModalOverlay` from the moderation page.

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
- **Automated Verification Disputes:** Implemented automatic recording of login attempts from non-UMak email addresses into the `verification_disputes` table. This ensures that administrators can review and manage restricted access cases directly from the Admin Hub.
- **Improved Restriction Feedback:** Updated the `unauthorized.html` page to inform users that their attempt has been logged and will be reviewed by administrators.
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
- **Admin Authorization Stale Session:** Fixed an issue where promoted users (e.g., `super_admin`) received "Unauthorized access" errors when accessing the Admin Hub. Updated the `admin_required` decorator to fetch the latest role from the database if the session role is outdated, ensuring seamless access after role updates.
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

### 5. Notifications & Warning System Polish
#### Added
- **Integrated Notification Center:** Added a real-time notification dropdown to both the main navbar and the Admin Hub sidebar.
- **Mark as Read:** Implemented functionality to mark notifications as read, updating the UI and database state immediately.
- **Global Notification Context:** Added a backend context processor to automatically inject unread notification counts and recent alerts into all templates.
- **Admin Warning UI:** Integrated the "Warn Author" modal directly into the Content Moderation post view, allowing admins to issue warnings while reviewing content.
- **Enhanced Warning Logic:** Updated the warning system to use a dedicated service client, ensuring admins can issue warnings and create notifications regardless of user RLS policies.

#### Fixed
- **Admin Role Verification:** Refactored the `admin_required` decorator to use a service client for role verification, fixing potential "Unauthorized" issues caused by RLS restrictions on the `profiles` table.
- **Modal Label Formatting:** Cleaned up modal metadata labels (Location, Date) by removing redundant emojis for a cleaner, more professional look.
- **Flash Message System:** Enhanced the global toast system to support dynamic JavaScript-triggered messages (`createToast`), ensuring consistent feedback for async actions like issuing warnings or marking notifications as read.

#### Fixed
- **Notification UI Readability & Spacing:** Significantly improved the notification dropdown visibility and breathing room.
    - Increased dropdown width from `w-80` to `w-96`.
    - Upscaled font sizes for titles (`text-[15px]`), messages (`text-[13px]`), and dates.
    - Added generous horizontal padding (**`px-8`**) across all sections to ensure text has ample breathing room from the edges.
    - Enhanced vertical spacing and internal padding for a more open, modern feel.
    - Increased the max-height of the scrollable area to `32rem` to show more alerts at once.

---
**Technical Note:** New migration files have been added to the `supabase/migrations/` directory, including `20260514000500_fix_warnings_policies.sql` for RLS security and `20260514000600_sync_notifications_schema.sql` for schema alignment. Ensure they are applied to the Supabase instance to enable the new database fields, reporting table, and RPC functions.
