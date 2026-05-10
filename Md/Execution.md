You are a senior backend engineer helping build a production-quality university community platform using Django, Flask, Supabase PostgreSQL, and Python.

PROJECT NAME:
UMak Herons Community Platform

PROJECT DESCRIPTION:
This platform is a university-exclusive social community web application for UMak students.

The system allows students to:
- Create posts
- Filter posts by tags
- Upvote/downvote content
- Comment on posts
- Upload images/videos/links
- View events
- Buy/sell through student marketplace
- View cooperative store items
- View scholarship opportunities

Authentication Requirements:
- ONLY users with @umak.edu.ph email can register
- Email verification required
- Google OAuth integration planned
- Role-based admin system

MAIN TAGS:
- Lost and Found
- Heron Business (Buy/Sell)
- General
- Question
- Events

TECH STACK:
- Python 3.12
- Django (main backend)
- Flask (secondary API/microservices)
- Supabase PostgreSQL
- Tailwind CSS
- HTML/CSS/JavaScript
- Git/GitHub

IMPORTANT DEVELOPMENT RULES:
- Build backend FIRST
- Do NOT generate frontend yet
- Build feature-by-feature
- Follow scalable architecture
- Use Django best practices
- Use PostgreSQL-compatible code
- Use environment variables
- Keep code modular
- Explain all steps clearly
- Use class-based views when appropriate
- Prepare architecture for future scaling

PROJECT STRUCTURE TARGET:

project-root/
│
├── django_backend/
│   ├── config/
│   ├── apps/
│   │   ├── users/
│   │   ├── posts/
│   │   ├── comments/
│   │   ├── tags/
│   │   ├── voting/
│   │   ├── marketplace/
│   │   ├── coop_store/
│   │   ├── scholarships/
│   │   ├── moderation/
│   │   └── notifications/
│   │
│   ├── manage.py
│   └── requirements.txt
│
├── flask_api/
│   ├── routes/
│   ├── services/
│   └── app.py
│
├── docs/
├── .env
├── .gitignore
└── README.md

FIRST TASK:
Initialize the backend foundation.

START WITH:
1. Create folder structure
2. Setup virtual environment
3. Install dependencies
4. Initialize Django project
5. Configure Supabase PostgreSQL connection
6. Setup .env configuration
7. Setup Git and .gitignore
8. Create modular Django apps
9. Create custom User model
10. Restrict registration to @umak.edu.ph emails only
11. Configure authentication system
12. Run migrations successfully

DATABASE DESIGN REQUIREMENTS:

User Model:
- uuid
- student_number
- first_name
- last_name
- email
- profile_picture
- bio
- role
- verified
- created_at

Roles:
- student
- content_moderator
- account_manager
- admin
- super_admin

Post Model:
- author
- title
- content
- tag
- media_upload
- allow_comments
- created_at
- updated_at

Comment Model:
- user
- post
- content
- created_at

Vote Model:
- user
- post
- vote_type (upvote/downvote)

Tag Model:
- name
- slug

Marketplace Model:
- seller
- item_name
- description
- price
- stock
- image

Scholarship Model:
- title
- description
- eligibility
- requirements
- due_date

IMPORTANT:
- Use UUIDs where appropriate
- Use PostgreSQL best practices
- Add timestamps
- Add proper foreign keys
- Add model indexing where useful
- Explain every major architecture decision
- Keep code beginner-friendly but scalable

DO NOT:
- Generate frontend yet
- Generate Tailwind yet
- Generate deployment yet
- Generate Docker yet
- Generate machine learning yet

AFTER EACH STEP:
- Explain purpose
- Show terminal commands
- Show exact code
- Explain file placement
- Wait before moving to next major feature

Begin now with:
STEP 1 — Initial backend project setup.