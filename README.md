# Herons' Hub - University of Makati Community Platform

Herons' Hub is a verified campus community platform built exclusively for University of Makati (UMak) students. It provides a unified space for sharing campus updates, discovering scholarships, browsing the UMak Coop catalog, joining events, and connecting through verified `@umak.edu.ph` school identities.

The platform enforces identity verification, content moderation, and role-based access to keep discussions relevant, safe, and student-focused.

**Live:** [heronshub.social](https://heronshub.social)
**Admin Portal:** [dev.heronshub.social](https://dev.heronshub.social)

---

## Features

### Student-Facing

- **Verified-Only Access** — Only `@umak.edu.ph` accounts can register, ensuring a trusted campus community.
- **Multi-Step Onboarding** — Guided registration flow with community guidelines, academic info collection (college, course, year level), and profile setup.
- **Dashboard Feed** — Infinite-scrolling post feed with category filtering, skeleton loading, and real-time sync.
- **Post Creation** — Create posts with multi-image uploads (Facebook-style grid), event scheduling, and category tagging (General, Buy & Sell, Events, Lost & Found).
- **Interactions** — Like, comment, and reply to posts with real-time updates and optimistic UI.
- **Real-Time Notifications** — Powered by Supabase Realtime with deep-linking to relevant content.
- **Event Calendar** — Browse and discover campus events with admin-approved scheduling.
- **Scholarship Catalog** — Searchable scholarship listings managed by admins.
- **UMak Coop Catalog** — University merchandise and coop items with AJAX filtering.
- **User Profiles** — Customizable profiles with social links, privacy controls, and academic info.
- **User Search** — Live directory search to find and connect with other students.
- **Embed Support** — Facebook, Instagram, and URL embeds in posts with iframe restrictions.
- **Pull-to-Refresh** — Mobile-friendly refresh for the dashboard feed.

### Admin Portal

- **Dashboard Overview** — Platform statistics, user breakdown, and pending action indicators.
- **User Management** — Full user directory with live search, online/offline status indicators, role assignment, and account sanctions (warnings, suspensions, bans).
- **Content Moderation** — Post approval queue, content flagging, and bulk moderation tools (approve, reject, delete).
- **Reports Queue** — Unified interface for reviewing reported posts and accounts with categorized reasons.
- **Managed Sanctions** — Centralized view of all active warnings, suspensions, and bans.
- **Global Admin Search** — Universal search across profiles, posts, reports, and admin navigation.
- **Academic Unit Management** — CRUD for colleges/institutes with dynamic brand colors.
- **Dynamic Course Dropdowns** — College-dependent course selection populated from a verified catalog of 60+ UMak programs.
- **Profanity Filter** — Multi-layer content moderation with exact match, elongation collapsing, leetspeak normalization, fuzzy matching, and toxic phrase detection. Managed via admin interface with database-backed word lists.
- **Landing Page Editor** — Full CMS for the public landing page: hero text, about section, feature cards (with icon picker), team section, and footer — all editable from the admin panel.
- **Team Management** — Upload a group team photo and set a lead developer card for the landing page.
- **Scholarship & Coop Catalog Management** — Add, edit, and remove catalog items with image uploads.
- **System Audit Logs** — Timestamped log of all admin actions with filtering.
- **Domain Separation** — Admin portal runs on a separate subdomain (`dev.`) with enforced routing.

### Platform

- **Smart Profanity Detection** — 5-layer system: exact/substring match, elongation collapsing, leetspeak normalization, fuzzy matching, and toxic phrase regex patterns. Supports English, Filipino, Hindi, Spanish, and Arabic terms.
- **Auto-Moderation** — Progressive enforcement: warnings at threshold, automatic suspension after repeated violations, with configurable cooldown periods.
- **Comment Spam Protection** — Backend rate limiting (3s cooldown) and frontend debounce to prevent duplicate submissions.
- **Activity Heartbeat** — Throttled middleware that tracks user activity for online/offline status.
- **Notification Deduplication** — Merged like notifications, ghost notification protection, and scope separation between user and admin layers.

---

## Tech Stack

### Backend

| Technology | Purpose |
|---|---|
| **Python 3** | Server-side language |
| **Flask 3.1** | Web framework |
| **Gunicorn** | WSGI HTTP server |
| **SQLAlchemy 2.0** | ORM / database toolkit |
| **Flask-WTF** | CSRF protection |

### Database & Auth

| Technology | Purpose |
|---|---|
| **Supabase** | Backend-as-a-Service (PostgreSQL, Auth, Realtime, Storage) |
| **PostgreSQL** | Primary database |
| **Supabase Auth (GoTrue)** | OAuth authentication with `@umak.edu.ph` verification |
| **Supabase Realtime** | WebSocket subscriptions for live notifications |
| **Supabase Storage** | Image uploads (posts, catalog items, team photos) |

### Frontend

| Technology | Purpose |
|---|---|
| **Jinja2** | Server-side HTML templating |
| **Tailwind CSS 3.4** | Utility-first CSS framework |
| **Alpine.js** | Lightweight JS framework for admin UI interactions |
| **Vanilla JavaScript** | Client-side interactivity, modals, real-time sync |
| **PostCSS + Autoprefixer** | CSS processing pipeline |

### Deployment

| Technology | Purpose |
|---|---|
| **DigitalOcean App Platform** | Cloud hosting (Singapore region) |
| **Custom Domains** | `heronshub.social` (public) / `dev.heronshub.social` (admin) |

---

## Project Structure

```
Intpt-Webdev/
├── .do/
│   └── app.yaml                    # DigitalOcean deployment config
├── flask_backend/
│   ├── app/
│   │   ├── __init__.py             # App factory, middleware, domain routing
│   │   ├── routes/
│   │   │   ├── core.py             # User-facing routes & API
│   │   │   ├── admin.py            # Admin portal routes
│   │   │   └── auth.py             # Authentication & onboarding
│   │   ├── utils/
│   │   │   ├── content_moderation.py  # Multi-layer profanity detection
│   │   │   └── post_archive.py     # Post archival utilities
│   │   ├── templates/              # Jinja2 HTML templates
│   │   │   ├── admin/              # Admin portal pages
│   │   │   ├── includes/           # Shared components (navbar, modal, post card)
│   │   │   └── *.html              # User-facing pages
│   │   ├── static/
│   │   │   ├── css/                # Compiled Tailwind + custom styles
│   │   │   ├── js/                 # Client-side JavaScript
│   │   │   └── images/             # Static assets & SVGs
│   │   └── services/
│   │       └── supabase_client.py  # Supabase client initialization
│   ├── tests/                      # Unit tests
│   ├── requirements.txt            # Python dependencies
│   ├── tailwind.config.js          # Tailwind theme configuration
│   └── package.json                # Node dependencies (Tailwind build)
├── supabase/
│   └── migrations/                 # Database schema migrations
├── Change_Log.md                   # Detailed feature changelog
└── README.md
```

---

## Local Development

### Prerequisites

- Python 3.10+
- Node.js 18+
- A Supabase project with Auth, Database, Realtime, and Storage enabled

### Setup

```bash
# Clone the repository
git clone https://github.com/Ic3krem/Intpt-Webdev.git
cd Intpt-Webdev/flask_backend

# Install Python dependencies
pip install -r requirements.txt

# Install Node dependencies (for Tailwind CSS)
npm install

# Configure environment variables
cp .env.example .env
# Edit .env with your Supabase credentials and Flask secret key

# Build Tailwind CSS
npm run build

# Run the development server
flask run
```

### Environment Variables

| Variable | Description |
|---|---|
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_KEY` | Supabase anon/public key |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase service role key (admin operations) |
| `DATABASE_URL` | PostgreSQL connection string |
| `SECRET_KEY` | Flask session secret |
| `ADMIN_DOMAIN` | Admin portal domain (e.g., `dev.heronshub.social`) |
| `MAIN_DOMAIN` | Public site domain (e.g., `heronshub.social`) |

### Tailwind CSS

```bash
# Watch mode (development)
npm run dev

# Production build (minified)
npm run build
```

### Running Tests

```bash
cd flask_backend
python -m pytest tests/
```

---

## Database Migrations

SQL migrations are located in `supabase/migrations/`. Run them in order via the Supabase SQL Editor or CLI:

```bash
supabase db push
```

---

## Team

Built by UMak students for UMak students.

---

## License

This project is developed for academic purposes at the University of Makati.
