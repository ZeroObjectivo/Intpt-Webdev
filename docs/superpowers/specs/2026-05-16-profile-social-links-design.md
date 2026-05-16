# Profile Social Links Design

Date: 2026-05-16
Owner: Codex
Status: Draft for review

## Goal

Add an interactive social-links setup to the profile dashboard so users can manage up to three social profile links from the existing profile edit modal, while keeping the experience lightweight and visually consistent with the rest of the profile settings UI.

This revised version should:
- allow up to 3 optional social links per user
- support `facebook.com`, `instagram.com`, `tiktok.com`, `linkedin.com`, and `discord.com`
- detect the platform automatically from the pasted URL
- store privacy per individual link
- display only public links on the profile dashboard
- keep the interaction dynamic with a compact initial state and an expandable configuration state

## Scope

In scope:
- database support for per-user social links with per-link visibility
- backend loading and saving of social links together with profile updates
- server-side URL validation and platform detection for the supported platforms
- profile edit modal UI with a two-state interactive social-links section
- dynamic add/remove behavior for up to 3 links
- public profile rendering of saved public links only
- tests for parsing, validation, visibility behavior, and rendering

Out of scope for v2:
- analytics or click tracking
- custom display labels per link
- drag-and-drop ordering
- social embeds or previews
- arbitrary websites beyond the approved social platforms

## Recommended Data Model

Keep using a separate `profile_social_links` table instead of adding columns to `profiles`.

### Table: `profile_social_links`

Fields:
- `id`
- `profile_id`
- `platform`
- `url`
- `visibility`
- `position`
- `created_at`
- `updated_at`

Recommended semantics:
- `profile_id` references `profiles.id`
- one row represents one saved social link
- `platform` stores normalized values like `facebook`, `instagram`, `tiktok`, `linkedin`, or `discord`
- `url` stores the normalized canonical URL
- `visibility` stores `public` or `only_me`
- `position` stores display/input order from 1 to 3

Recommended constraints:
- foreign key from `profile_social_links.profile_id` to `profiles.id`
- unique constraint on (`profile_id`, `position`)
- unique constraint on (`profile_id`, `url`) to prevent duplicates
- check constraint for `platform`
- check constraint for `visibility`

Why this model:
- keeps `profiles` clean
- supports future platform growth without redesigning the profile table
- keeps visibility independent per link
- supports public rendering and private owner-only management cleanly

## Backend Behavior

### Profile Load

Extend the profile load path so it fetches social links for the viewed profile and returns them ordered by `position`.

Expected payload addition:
- `social_links`: ordered list of link objects for the profile owner view
- `public_social_links`: filtered list of links with `visibility = public` for public rendering

Each display object should include:
- `platform`
- `url`
- `label`
- `visibility`
- `position`

For v2, labels can still be generated from the normalized platform:
- `Facebook`
- `Instagram`
- `TikTok`
- `LinkedIn`
- `Discord`

### Profile Update

Keep social links inside the existing profile edit submit.

The profile update flow should:
1. read up to 3 social link rows from the form
2. treat each row as a pair of values:
   - `url`
   - `visibility`
3. trim and ignore rows where the URL is empty
4. validate each non-empty URL
5. detect the platform from the URL
6. validate the visibility value for each non-empty row
7. reject the entire update if any row is invalid
8. replace the user's saved social links with the validated set

This should behave transactionally from the user's perspective:
- if any social link row is invalid, no social link changes should be saved
- the profile update should not partially succeed in a confusing way

## Validation Rules

### Accepted Domains

Only these platforms are valid in this version:
- `facebook.com`
- `instagram.com`
- `tiktok.com`
- `linkedin.com`
- `discord.com`

The validator should also accept standard subdomain variants where appropriate, such as:
- `www.facebook.com`
- `m.facebook.com`
- `www.instagram.com`
- `www.tiktok.com`
- `www.linkedin.com`

### Rejected Inputs

Reject:
- unsupported domains
- malformed URLs
- duplicate links in the same submission
- more than 3 non-empty links
- invalid visibility values

### Normalization

Normalization should:
- trim whitespace
- ensure scheme is present
- normalize host casing
- remove obvious trailing slash noise where safe

Platform detection should map supported hosts to:
- `facebook`
- `instagram`
- `tiktok`
- `linkedin`
- `discord`

### Error Messages

Use clear user-facing messages such as:
- `Only supported social media links can be saved right now.`
- `Please enter valid social profile URLs.`
- `You can save up to 3 social links only.`
- `Duplicate social links are not allowed.`
- `Please choose a valid visibility setting for each social link.`

## Interaction Design

The social-links section inside the profile edit modal should use a two-state interaction model.

### Workflow 1: Initial State

This is the compact state shown when the user has no active row open yet.

Elements:
- section title: `Social Links`
- helper text: `Add up to 3 social links.`
- primary trigger: `Add social links`

Behavior:
- clicking `Add social links` expands the UI into the configuration state
- this transition should feel smooth and lightweight
- if there are already saved links, the section may initialize in an expanded editable state instead of feeling empty

### Workflow 2: Configuration State

This is the editable dynamic state.

Each row includes:
- one URL input only
- one privacy control with:
  - `Public`
  - `Only me`
- one remove action

Behavior:
- no platform selector is shown to the user
- the platform is auto-detected from the URL
- the user can add rows until they reach 3
- the user can remove rows freely
- a cancel action should allow the user to back out of creating a new row when appropriate
- if the user opens the composer and enters nothing, cancel should collapse back to the initial state

## UI Design

### Edit Modal

Revise the existing `Social Links` section into an interactive module within the profile edit modal.

Visual approach:
- reuse the modal’s current spacing, border, radius, typography, and button language
- keep the compact state visually light so it does not dominate the form
- use subtle transitions only for expand/collapse and row appearance
- avoid introducing extra fields like descriptions or platform pickers

Dynamic section behavior:
- compact first state with `Add social links`
- expandable editing area with one or more rows
- maximum of 3 rows
- each row can be removed independently

### Public Profile Display

Render only public social links below the profile metadata pills and above the bio.

Display style:
- pill/button style links
- subtle platform cue or label
- consistent with current profile card styling
- open in a new tab

Display rules:
- render only links where `visibility = public`
- preserve saved order by `position`
- if no public links exist, show nothing

## Route and Template Changes

Likely impacted areas:
- `flask_backend/app/routes/core.py`
- `flask_backend/app/templates/profile_settings.html`
- `flask_backend/tests/test_profile_social_links.py`
- `flask_backend/tests/test_profile_settings_template.py`
- Supabase migration files for the updated schema

Expected backend additions:
- expanded social URL validator for the supported platforms
- visibility validation per row
- helper logic to filter public vs owner-visible links
- schema migration for `visibility`

Expected template additions:
- two-state dynamic social-links section in the edit modal
- row-based inputs for URL + privacy + remove
- public-only social links strip on the profile header

## Migration / Rollout Notes

Migration updates needed:
- ensure `profile_social_links` exists
- add `visibility` column if it does not already exist
- backfill existing rows to `public` by default
- add a `visibility` check constraint

Rollout assumptions:
- existing rows from the first version should remain valid
- existing users without social links remain unaffected
- users with earlier saved links should continue to work after the visibility migration

## Testing Plan

### Backend Tests

Add or update tests for:
- Facebook URL detection
- Instagram URL detection
- TikTok URL detection
- LinkedIn URL detection
- Discord URL detection
- unsupported domain rejection
- malformed URL rejection
- duplicate link rejection
- max-3 enforcement
- invalid visibility rejection
- default/public visibility migration assumptions where needed

### Template Tests

Add rendering coverage for:
- `Add social links`
- `Add up to 3 social links.`
- row URL inputs
- row visibility controls
- remove/cancel controls
- public-only profile link rendering

### Regression Checks

Verify:
- existing profile updates still work without social links
- profile page still renders for users with no links
- private links do not appear on the public profile
- own profile edit view can still manage all saved links

## Risks

### URL Parsing Ambiguity

Some supported platforms have multiple URL formats. The validator should be permissive enough for normal profile URLs while still strict about host safety.

### Dynamic Form Complexity

The new two-state UI introduces more client-side interaction than the first version. The implementation should keep the JS lightweight and scoped to the profile modal to avoid fragile behavior.

### Privacy Confusion

If privacy is not clearly attached to each row, users may misunderstand which links are public. The row layout should make that relationship obvious.

## Final Recommendation

Implement the revised social-links feature as an inline two-state module inside the existing profile edit modal, backed by the `profile_social_links` table with per-link `visibility`, automatic platform detection, support for Facebook, Instagram, TikTok, LinkedIn, and Discord, and public rendering only for links marked `public`.
