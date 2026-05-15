# Local Domain Testing (User + Admin)

This guide helps you run and test both local flows:

- User flow (`localhost`)
- Admin flow (`dev.localhost`)

It also includes the main local authentication pitfall discovered on May 16, 2026 so the same setup issue is easier to catch in the future.

## Prerequisites

Before testing local domains, confirm:

- Python 3.12+ is installed
- Node.js and npm are installed
- `flask_backend\.env` is present
- you can edit the Windows hosts file with Administrator privileges
- the Flask server has been restarted after any auth-related code changes

## Precautions

- Keep `MAIN_DOMAIN=localhost` and `ADMIN_DOMAIN=dev.localhost` in local `.env`.
- Do not test admin-domain behavior only from `localhost`.
- Do not assume failed login means broken Supabase credentials.
- Check local proxy variables if one machine fails while another succeeds with the same `.env`.
- Never commit tokens, `.env`, or copied browser callback URLs.

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
- `MAIN_DOMAIN` should stay `localhost`.
- `ADMIN_DOMAIN` should stay `dev.localhost`.

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

6. Login ends with `Authentication failed. Please try again.`
- Cause: possible dead machine-level proxy values, stale Flask process, or missing `dev.localhost` mapping.
- Fix:
  - restart Flask
  - confirm hosts entry exists
  - check `HTTP_PROXY`, `HTTPS_PROXY`, and `ALL_PROXY`

7. Same `.env` works for another developer but not for this machine
- Cause: local shell or OS runtime mismatch rather than repo credentials.
- Fix:
  - compare proxy environment variables
  - compare whether `dev.localhost` resolves locally
  - verify local firewall or proxy tooling is not intercepting Python traffic

## 8) Proxy environment check

Run this in PowerShell:

```powershell
cmd /c set HTTP
cmd /c set HTTPS
cmd /c set ALL_PROXY
cmd /c set NO_PROXY
```

Be cautious if you see values like:

```env
HTTP_PROXY=http://127.0.0.1:9
HTTPS_PROXY=http://127.0.0.1:9
ALL_PROXY=http://127.0.0.1:9
```

That pattern can break Supabase auth calls locally even when `.env` is correct.

## 9) References

- `RUNNING.md`

## 10) Local setup summary

This is the short handoff version of the local setup requirements and the main auth issue found during testing.

Required local setup:

- Python 3.12+
- Node.js 16+
- Git
- `flask_backend\.env` with valid Supabase and database values
- `MAIN_DOMAIN=localhost`
- `ADMIN_DOMAIN=dev.localhost`
- Windows hosts entry for `dev.localhost`

Recommended run flow:

1. Start Flask from `flask_backend` using the project virtual environment.
2. Start the Tailwind watcher in a second terminal.
3. Test both:
   - `http://localhost:5000/login`
   - `http://dev.localhost:5000/login`

Important precautions:

- Do not commit `.env`.
- Restart Flask after changing auth code or environment values.
- Do not assume Supabase credentials are bad just because local login fails.
- Compare machine-level environment variables when one developer can log in and another cannot.

Recommended first checks when local login breaks:

1. Restart the Flask server.
2. Check the hosts file for `dev.localhost`.
3. Check `HTTP_PROXY`, `HTTPS_PROXY`, and `ALL_PROXY`.
4. Confirm `.env` is loaded from `flask_backend`.
5. Re-test the login flow on the intended host.

## 11) Local auth incident report - 2026-05-16

Title:

Local login failure on `localhost` and `dev.localhost` despite valid Supabase credentials

Date:

May 16, 2026

Affected area:

- local Google OAuth login
- `/auth/session` session finalization route
- Flask Supabase auth/PostgREST/storage clients

Reported symptom:

After Google sign-in, the browser was redirected to:

`http://dev.localhost:5000/auth/session?...`

The page then showed:

`Authentication failed. Please try again.`

Initial assumptions ruled out:

- invalid Supabase URL
- invalid anon key or service role key
- invalid OAuth token
- broken `@umak.edu.ph` restriction logic
- incorrect local domain values in `.env`

This was supported by the fact that another developer could run the app locally using the same `.env` values.

Root cause:

The local machine had inherited proxy environment variables set to a dead local proxy:

```env
HTTP_PROXY=http://127.0.0.1:9
HTTPS_PROXY=http://127.0.0.1:9
ALL_PROXY=http://127.0.0.1:9
NO_PROXY=localhost,127.0.0.1,::1
```

The Python Supabase stack uses `httpx`, and its default clients honor environment proxy settings through `trust_env=True`.

As a result:

1. Flask received a valid OAuth token.
2. The app attempted to call Supabase Auth using that token.
3. The outbound request was sent to the dead local proxy instead of Supabase.
4. The request failed with `ConnectError [WinError 10061]`.
5. `/auth/session` returned the generic authentication failure page.

Evidence gathered:

- the returned access token resolved successfully once proxy inheritance was disabled for the test process
- before the fix, the Supabase auth call failed with `ConnectError [WinError 10061] No connection could be made because the target machine actively refused it`
- the issue affected one local machine only, while another developer could log in using the same repo and `.env`

Code changes made:

1. Auth bootstrap safety
- `flask_backend/app/routes/auth.py` was adjusted so the initial `profiles` lookup does not depend on the fresh user-scoped PostgREST client during session setup.

2. No-proxy Supabase client wrapper
- `flask_backend/services/supabase_client.py` now constructs Supabase auth, PostgREST, and storage clients with proxy environment inheritance disabled.

Verification performed:

- access token resolved to `rcervantes.9168@umak.edu.ph`
- public profile lookup returned the expected profile row
- local regression tests passed

Verification command:

```powershell
venv\Scripts\python -m unittest flask_backend.tests.test_auth_session flask_backend.tests.test_local_domain_routing -v
```

Files involved:

- `flask_backend/services/supabase_client.py`
- `flask_backend/app/routes/auth.py`
- `flask_backend/tests/test_auth_session.py`
- `flask_backend/tests/test_local_domain_routing.py`

Precautions for future setup:

- Check machine-level proxy environment variables before rotating API credentials.
- Restart the Flask server after auth-related code or environment changes.
- Keep `MAIN_DOMAIN=localhost` and `ADMIN_DOMAIN=dev.localhost` in local `.env`.
- Ensure `dev.localhost` is mapped in the Windows hosts file.
- Treat "works on another machine with the same `.env`" as a strong signal to inspect shell and OS runtime differences.

Short conclusion:

The failure was caused by local proxy environment pollution, not by invalid Supabase credentials. The repository now contains a defensive fix so local auth does not depend on machine proxy state by default.

