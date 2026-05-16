# Profile Social Links Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an interactive social-links setup with up to three user-managed social profiles, per-link visibility, and public-only profile display on the dashboard.

**Architecture:** Keep profile social data normalized in the `profile_social_links` table keyed by `profiles.id`, extend it with per-link `visibility`, and continue saving it through the existing profile update submit. Validate and normalize URLs server-side, auto-detect supported platforms, render only public links in the dashboard header, and expose a dynamic two-state social-links module in the edit modal.

**Tech Stack:** Flask, Supabase/PostgREST, Supabase SQL migrations, Jinja templates, lightweight modal JavaScript, unittest, existing profile dashboard/modal UI

---

## File Structure

### Existing files to modify

- `flask_backend/app/routes/core.py`
  - Add social-link query, validation, normalization, load, and update logic.
- `flask_backend/app/templates/profile_settings.html`
  - Add profile header social link pills and add a new `Social Links` section in the edit modal.
- `flask_backend/tests/test_profile_settings_template.py`
  - Extend template rendering coverage for the new social-link display and edit fields.

### New files to create

- `flask_backend/tests/test_profile_social_links.py`
  - Unit tests for validation, normalization, max-3 enforcement, and update payload behavior.
- `docs/sql/profile_social_links.sql`
  - SQL migration/reference script for creating the `profile_social_links` table and its constraints.

### Responsibilities

- `core.py` remains the single backend integration point for profile dashboard loading and profile edit saving.
- `profile_settings.html` remains the single view for both profile display and the edit modal UI.
- `test_profile_social_links.py` owns backend rules for accepted domains, duplicate rejection, and ordering.
- `test_profile_settings_template.py` owns rendering coverage for the profile-side presentation.
- `profile_social_links.sql` documents the required DB schema so teammates can apply it consistently.

---

### Task 1: Add Social Link Schema Reference

**Files:**
- Create: `docs/sql/profile_social_links.sql`

- [ ] **Step 1: Write the schema reference file**

```sql
create table if not exists public.profile_social_links (
    id uuid primary key default gen_random_uuid(),
    profile_id uuid not null references public.profiles(id) on delete cascade,
    platform text not null check (platform in ('facebook', 'instagram')),
    url text not null,
    position integer not null check (position between 1 and 3),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create unique index if not exists profile_social_links_profile_position_idx
    on public.profile_social_links (profile_id, position);

create unique index if not exists profile_social_links_profile_url_idx
    on public.profile_social_links (profile_id, url);
```

- [ ] **Step 2: Save the file and read it back**

Run:

```powershell
Get-Content docs/sql/profile_social_links.sql
```

Expected: the table definition plus both unique indexes

- [ ] **Step 3: Commit**

```bash
git add docs/sql/profile_social_links.sql
git commit -m "docs(db): add profile social links schema reference"
```

---

### Task 2: Add Failing Backend Tests For Social Link Rules

**Files:**
- Create: `flask_backend/tests/test_profile_social_links.py`
- Modify: `flask_backend/app/routes/core.py`

- [ ] **Step 1: Write failing tests for URL parsing and validation**

```python
import os
import sys
import unittest

os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault(
    "SUPABASE_KEY",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJyb2xlIjoiYW5vbiIsImlzcyI6InN1cGFiYXNlIn0."
    "test-signature",
)
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from app.routes.core import normalize_social_links_input


class ProfileSocialLinksValidationTest(unittest.TestCase):
    def test_accepts_facebook_and_instagram_links(self):
        links = normalize_social_links_input([
            "facebook.com/example.user",
            "https://www.instagram.com/example.user/",
        ])
        self.assertEqual(
            links,
            [
                {"platform": "facebook", "url": "https://facebook.com/example.user", "position": 1},
                {"platform": "instagram", "url": "https://www.instagram.com/example.user", "position": 2},
            ],
        )

    def test_rejects_unsupported_domain(self):
        with self.assertRaisesRegex(ValueError, "Only Facebook and Instagram links are supported right now."):
            normalize_social_links_input(["https://tiktok.com/@example"])

    def test_rejects_duplicate_links(self):
        with self.assertRaisesRegex(ValueError, "Duplicate social links are not allowed."):
            normalize_social_links_input([
                "https://facebook.com/example",
                "https://facebook.com/example/",
            ])

    def test_rejects_more_than_three_links(self):
        with self.assertRaisesRegex(ValueError, "You can save up to 3 social links only."):
            normalize_social_links_input([
                "https://facebook.com/one",
                "https://instagram.com/two",
                "https://facebook.com/three",
                "https://instagram.com/four",
            ])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```powershell
venv\Scripts\python -m unittest flask_backend.tests.test_profile_social_links -v
```

Expected: FAIL with import or missing function errors for `normalize_social_links_input`

- [ ] **Step 3: Commit**

```bash
git add flask_backend/tests/test_profile_social_links.py
git commit -m "test(profile): add social links validation coverage"
```

---

### Task 3: Implement Social Link Validation Helpers

**Files:**
- Modify: `flask_backend/app/routes/core.py`
- Test: `flask_backend/tests/test_profile_social_links.py`

- [ ] **Step 1: Add minimal helper implementations in `core.py`**

```python
from urllib.parse import urlparse, urlunparse
```

```python
def normalize_social_url(raw_url):
    candidate = (raw_url or "").strip()
    if not candidate:
        return None

    if "://" not in candidate:
        candidate = f"https://{candidate}"

    parsed = urlparse(candidate)
    host = (parsed.netloc or "").strip().lower()
    path = (parsed.path or "").strip()
    normalized_path = path.rstrip("/")

    if not host or not normalized_path:
        raise ValueError("Please enter valid social media profile URLs.")

    if host in {"facebook.com", "www.facebook.com", "m.facebook.com"}:
        platform = "facebook"
    elif host in {"instagram.com", "www.instagram.com"}:
        platform = "instagram"
    else:
        raise ValueError("Only Facebook and Instagram links are supported right now.")

    normalized_url = urlunparse(("https", host, normalized_path, "", "", ""))
    return platform, normalized_url


def normalize_social_links_input(raw_links):
    values = [(value or "").strip() for value in (raw_links or []) if (value or "").strip()]
    if len(values) > 3:
        raise ValueError("You can save up to 3 social links only.")

    results = []
    seen_urls = set()
    for index, value in enumerate(values, start=1):
        platform, normalized_url = normalize_social_url(value)
        if normalized_url in seen_urls:
            raise ValueError("Duplicate social links are not allowed.")
        seen_urls.add(normalized_url)
        results.append({
            "platform": platform,
            "url": normalized_url,
            "position": index,
        })
    return results
```

- [ ] **Step 2: Run backend validation tests**

Run:

```powershell
venv\Scripts\python -m unittest flask_backend.tests.test_profile_social_links -v
```

Expected: PASS for all social link validation tests

- [ ] **Step 3: Commit**

```bash
git add flask_backend/app/routes/core.py flask_backend/tests/test_profile_social_links.py
git commit -m "feat(profile): add social link validation helpers"
```

---

### Task 4: Load Social Links Into The Profile Dashboard

**Files:**
- Modify: `flask_backend/app/routes/core.py`
- Test: `flask_backend/tests/test_profile_settings_template.py`

- [ ] **Step 1: Add a helper to load ordered social links**

```python
def load_profile_social_links(client, user_id):
    response = client.table('profile_social_links')\
        .select("platform, url, position")\
        .eq("profile_id", user_id)\
        .order("position")\
        .execute()

    display_map = {
        "facebook": "Facebook",
        "instagram": "Instagram",
    }

    return [
        {
            "platform": row.get("platform"),
            "url": row.get("url"),
            "label": display_map.get(row.get("platform"), (row.get("platform") or "").title()),
            "position": row.get("position"),
        }
        for row in (response.data or [])
        if row.get("url")
    ]
```

- [ ] **Step 2: Wire the helper into `load_profile_data` and route rendering**

```python
social_links = load_profile_social_links(client, user_id)
```

```python
return profile, posts, interactions, college_options, social_links
```

```python
profile, posts, interactions, college_options, social_links = load_profile_data(...)
```

```python
return render_template(
    'profile_settings.html',
    user=profile,
    posts=posts,
    interactions=interactions,
    college_options=college_options,
    social_links=social_links,
    is_own_profile=is_own_profile,
    now=datetime.datetime.now(datetime.timezone.utc),
)
```

- [ ] **Step 3: Update the template render test context to include `social_links=[]` first**

```python
social_links=[],
```

- [ ] **Step 4: Run the existing template test**

Run:

```powershell
venv\Scripts\python -m unittest flask_backend.tests.test_profile_settings_template -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add flask_backend/app/routes/core.py flask_backend/tests/test_profile_settings_template.py
git commit -m "feat(profile): load social links into profile data"
```

---

### Task 5: Save Social Links In The Existing Profile Update Submit

**Files:**
- Modify: `flask_backend/app/routes/core.py`
- Test: `flask_backend/tests/test_profile_social_links.py`

- [ ] **Step 1: Add a failing test for social link payload extraction**

```python
from app.routes.core import normalize_social_links_input

class ProfileSocialLinksUpdateShapeTest(unittest.TestCase):
    def test_empty_values_are_ignored_and_positions_are_compact(self):
        links = normalize_social_links_input([
            "https://facebook.com/example",
            "",
            "instagram.com/example.user",
        ])
        self.assertEqual(
            links,
            [
                {"platform": "facebook", "url": "https://facebook.com/example", "position": 1},
                {"platform": "instagram", "url": "https://instagram.com/example.user", "position": 2},
            ],
        )
```

- [ ] **Step 2: Add replace-on-save logic inside `update_profile`**

```python
social_links_raw = [
    request.form.get('social_link_1', ''),
    request.form.get('social_link_2', ''),
    request.form.get('social_link_3', ''),
]
```

```python
normalized_social_links = normalize_social_links_input(social_links_raw)
```

```python
client.table('profile_social_links').delete().eq('profile_id', user_id).execute()
for link in normalized_social_links:
    client.table('profile_social_links').insert({
        "profile_id": user_id,
        "platform": link["platform"],
        "url": link["url"],
        "position": link["position"],
    }).execute()
```

```python
except ValueError as e:
    flash(str(e), "error")
    return redirect(url_for('core.view_profile', target_user_id=user_id))
```

- [ ] **Step 3: Run social link tests**

Run:

```powershell
venv\Scripts\python -m unittest flask_backend.tests.test_profile_social_links -v
```

Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add flask_backend/app/routes/core.py flask_backend/tests/test_profile_social_links.py
git commit -m "feat(profile): save social links with profile updates"
```

---

### Task 6: Add Social Link Inputs To The Edit Modal

**Files:**
- Modify: `flask_backend/app/templates/profile_settings.html`
- Test: `flask_backend/tests/test_profile_settings_template.py`

- [ ] **Step 1: Add the social links edit section to the modal**

```html
<section class="border-b border-slate-100 px-6 py-6 sm:px-8 sm:py-7">
    <h3 class="text-lg font-black text-slate-800 mb-2">Social Links</h3>
    <p class="mb-5 text-sm font-medium text-slate-500">Add up to 3 Facebook or Instagram profile links.</p>
    <div class="grid grid-cols-1 gap-4">
        <input type="url" name="social_link_1" class="profile-form-control w-full border border-slate-200 bg-slate-50 px-4 py-3 text-sm font-semibold text-slate-700 outline-none focus:border-umak-blue focus:bg-white" value="{{ social_links[0].url if social_links|length > 0 else '' }}" placeholder="https://facebook.com/yourprofile">
        <input type="url" name="social_link_2" class="profile-form-control w-full border border-slate-200 bg-slate-50 px-4 py-3 text-sm font-semibold text-slate-700 outline-none focus:border-umak-blue focus:bg-white" value="{{ social_links[1].url if social_links|length > 1 else '' }}" placeholder="https://instagram.com/yourprofile">
        <input type="url" name="social_link_3" class="profile-form-control w-full border border-slate-200 bg-slate-50 px-4 py-3 text-sm font-semibold text-slate-700 outline-none focus:border-umak-blue focus:bg-white" value="{{ social_links[2].url if social_links|length > 2 else '' }}" placeholder="Paste another Facebook or Instagram link">
    </div>
</section>
```

- [ ] **Step 2: Extend the template render test assertions**

```python
self.assertIn("Social Links", html)
self.assertIn("Add up to 3 Facebook or Instagram profile links.", html)
self.assertIn('name="social_link_1"', html)
self.assertIn('name="social_link_2"', html)
self.assertIn('name="social_link_3"', html)
```

- [ ] **Step 3: Run template test**

Run:

```powershell
venv\Scripts\python -m unittest flask_backend.tests.test_profile_settings_template -v
```

Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add flask_backend/app/templates/profile_settings.html flask_backend/tests/test_profile_settings_template.py
git commit -m "feat(profile): add social links inputs to profile modal"
```

---

### Task 7: Render Public Social Link Pills On The Profile Header

**Files:**
- Modify: `flask_backend/app/templates/profile_settings.html`
- Test: `flask_backend/tests/test_profile_settings_template.py`

- [ ] **Step 1: Add the public social-link strip below the metadata pills**

```html
{% if social_links %}
<div class="flex flex-wrap gap-3">
    {% for link in social_links %}
    <a href="{{ link.url }}"
       target="_blank"
       rel="noopener noreferrer"
       class="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white px-4 py-2 text-sm font-black text-slate-700 shadow-sm transition-all hover:-translate-y-0.5 hover:border-umak-blue hover:text-umak-blue">
        <span>{{ link.label }}</span>
        <svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14 3h7v7m0-7L10 14m-4 0H3v7h7"></path>
        </svg>
    </a>
    {% endfor %}
</div>
{% endif %}
```

- [ ] **Step 2: Extend the template render test input and assertions**

```python
social_links=[
    {"platform": "facebook", "url": "https://facebook.com/juan", "label": "Facebook", "position": 1},
    {"platform": "instagram", "url": "https://instagram.com/juan", "label": "Instagram", "position": 2},
],
```

```python
self.assertIn("Facebook", html)
self.assertIn("Instagram", html)
self.assertIn("https://facebook.com/juan", html)
self.assertIn("https://instagram.com/juan", html)
```

- [ ] **Step 3: Run the template test**

Run:

```powershell
venv\Scripts\python -m unittest flask_backend.tests.test_profile_settings_template -v
```

Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add flask_backend/app/templates/profile_settings.html flask_backend/tests/test_profile_settings_template.py
git commit -m "feat(profile): show public social links on profile dashboard"
```

---

### Task 8: Run Regression Verification

**Files:**
- Modify: none
- Test: `flask_backend/tests/test_profile_social_links.py`
- Test: `flask_backend/tests/test_profile_settings_template.py`
- Test: `flask_backend/tests/test_auth_session.py`
- Test: `flask_backend/tests/test_local_domain_routing.py`

- [ ] **Step 1: Run targeted profile and existing regression tests**

Run:

```powershell
venv\Scripts\python -m unittest flask_backend.tests.test_profile_social_links flask_backend.tests.test_profile_settings_template flask_backend.tests.test_auth_session flask_backend.tests.test_local_domain_routing -v
```

Expected: all tests PASS

- [ ] **Step 2: Run diff check**

Run:

```powershell
git diff --check
```

Expected: no whitespace or conflict-marker errors, aside from any pre-existing CRLF warnings

- [ ] **Step 3: Commit**

```bash
git add flask_backend/app/routes/core.py flask_backend/app/templates/profile_settings.html flask_backend/tests/test_profile_social_links.py flask_backend/tests/test_profile_settings_template.py docs/sql/profile_social_links.sql
git commit -m "feat(profile): add social links to profile dashboard"
```

---

## Self-Review

### Spec coverage

- Separate social-links table: covered in Task 1
- Same profile edit submit: covered in Task 5
- Free-form URL inputs with backend detection: covered in Tasks 3, 5, and 6
- Only Facebook and Instagram accepted: covered in Task 3
- Public dashboard display: covered in Task 7
- Tests for backend and rendering: covered in Tasks 2, 4, 6, 7, and 8

### Placeholder scan

- No `TODO` or `TBD`
- Commands are explicit
- Code steps include actual snippets

### Type consistency

- Backend helper output always uses `platform`, `url`, and `position`
- Public display uses `platform`, `url`, `label`, and `position`
- Form fields are consistently named `social_link_1`, `social_link_2`, `social_link_3`
