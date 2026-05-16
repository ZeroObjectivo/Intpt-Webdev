# Profile Social Links Summary

Date: 2026-05-16
Feature: Profile Social Links

## What was added

- Added `profile_social_links` support for user-managed social profile URLs linked to `profiles.id`.
- Added per-link visibility with `public` and `only_me`.
- Expanded supported platforms to:
  - Facebook
  - Instagram
  - TikTok
  - LinkedIn
  - Discord

## Backend updates

- Added URL normalization and platform detection in `flask_backend/app/routes/core.py`.
- Added validation for:
  - supported domains only
  - max of 3 links
  - duplicate rejection
  - valid per-link visibility
- Updated profile load behavior to:
  - load all social links for the profile owner edit view
  - expose only public links for profile header display
- Kept save behavior inside the existing profile edit submit flow.

## UI/UX updates

- Added a two-state `Social Links` section inside the profile edit modal.
- Added dynamic add/remove behavior for up to 3 links.
- Added per-link visibility controls.
- Reworked the social-link rows for better spacing and field balance.
- Replaced text-only detected platform badges with neutral icon-based badges.
- Updated public profile pills to show the platform icon on the left of the platform name.

## Database updates

- Added base migration for `profile_social_links`.
- Added follow-up migration for:
  - `visibility`
  - platform expansion
  - visibility constraint
- Updated the SQL reference doc to match the latest table shape.

## Verification

Passed:

```powershell
venv\Scripts\python -m unittest flask_backend.tests.test_profile_social_links flask_backend.tests.test_profile_settings_template flask_backend.tests.test_auth_session flask_backend.tests.test_local_domain_routing -v
```

## Notes

- Existing links are backfilled to `public`.
- Private links remain editable by the owner but do not render publicly on the profile header.
