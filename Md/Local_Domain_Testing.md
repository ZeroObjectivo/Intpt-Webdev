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
DATABASE_URL=postgresql+psycopg2://postgres:<DB_PASSWORD>@db.<project-ref>.supabase.co:5432/postgres

MAIN_DOMAIN=localhost
ADMIN_DOMAIN=dev.localhost
```

Important:

- `DATABASE_URL` must be a Postgres SQLAlchemy URL (`postgresql+psycopg2://...`), not `https://...`.
- Keep secrets local only. Do not commit `.env`.

## 2) Map local admin host (required for `dev.localhost`)

Run this once in **PowerShell as Administrator**:

```powershell
Add-Content -Path "C:\Windows\System32\drivers\etc\hosts" -Value "`n127.0.0.1 dev.localhost"
```

## 3) Run backend + css watcher

Terminal A:

```powershell
cd C:\Users\<your-user>\Desktop\Intpt-Webdev
.\.venv\Scripts\Activate.ps1
cd flask_backend
python run.py
```

Terminal B:

```powershell
cd C:\Users\<your-user>\Desktop\Intpt-Webdev\flask_backend
npm run dev
```

## 4) Open local URLs

- User side: `http://localhost:5000/login`
- Admin side: `http://dev.localhost:5000/login`

`dev.localhost` should resolve to your local machine in modern browsers.

## 5) Role-based admin access from user side

Users with these roles can see **Admin Dashboard** in the user settings dropdown:

- `account_manager`
- `content_moderator`
- `content_manager`
- `admin`
- `super_admin` / `superadmin`

## 6) Quick realtime check

1. Open user and admin in separate tabs.
2. Delete a post from admin.
3. Confirm post disappears on both sides with ~300ms UI delay.
4. Trigger a notification and confirm realtime appearance.

## 7) Common local errors from migration and fixes

1. `RuntimeError: SECRET_KEY environment variable is not set.`
- Fix: ensure `.env` is in `flask_backend/.env` and contains `SECRET_KEY=...`.

2. `sqlalchemy.exc.NoSuchModuleError: Can't load plugin: sqlalchemy.dialects:https`
- Cause: `DATABASE_URL` is set to an HTTPS URL.
- Fix: replace with `postgresql+psycopg2://postgres:<DB_PASSWORD>@db.<project-ref>.supabase.co:5432/postgres`.

3. `Access to hosts is denied`
- Cause: editing `C:\Windows\System32\drivers\etc\hosts` in non-admin terminal.
- Fix: run hosts update command in **Administrator** PowerShell.

4. `can't open file ...\run.py`
- Cause: running from repo root.
- Fix: `cd flask_backend` first, then run `python run.py`.

5. PowerShell command parsing errors while copying from chat
- Cause: pasting prompt text (`PS C:\...>`) or multiple commands into one line.
- Fix: paste only the command body, one command per line.

