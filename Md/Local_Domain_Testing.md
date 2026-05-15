# Local Domain Testing (User + Admin)

This guide helps you run and test both local flows:

- User flow (`localhost`)
- Admin flow (`dev.localhost`)

## 1) Set local env values

Create/update `flask_backend/.env`:

```env
SECRET_KEY=your-local-secret
FLASK_ENV=development
FLASK_DEBUG=True

SUPABASE_URL=your-supabase-url
SUPABASE_KEY=your-supabase-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-supabase-service-role-key

MAIN_DOMAIN=localhost
ADMIN_DOMAIN=dev.localhost
```

## 2) Run backend + css watcher

Terminal A:

```powershell
cd flask_backend
.\venv\Scripts\Activate.ps1
python run.py
```

Terminal B:

```powershell
cd flask_backend
npm run dev
```

## 3) Open local URLs

- User side: `http://localhost:5000/login`
- Admin side: `http://dev.localhost:5000/login`

`dev.localhost` should resolve to your local machine in modern browsers.

## 4) Role-based admin access from user side

Users with these roles can see **Admin Dashboard** in the user settings dropdown:

- `account_manager`
- `content_moderator`
- `content_manager`
- `admin`
- `super_admin` / `superadmin`

## 5) Quick realtime check

1. Open user and admin in separate tabs.
2. Delete a post from admin.
3. Confirm post disappears on both sides with ~300ms UI delay.
4. Trigger a notification and confirm realtime appearance.

