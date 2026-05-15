# How to Run the UMak Herons Community Platform

This document provides step-by-step instructions for setting up and running the application locally.

---

## Prerequisites

Before getting started, ensure you have the following installed:

- **Python 3.12+** - [Download here](https://www.python.org/downloads/)
- **Node.js 16+** and **npm** - [Download here](https://nodejs.org/)
- **Git** - [Download here](https://git-scm.com/)
- **Supabase CLI** (optional, for database management) - [Download here](https://supabase.com/docs/guides/cli)

### Verify Installations

```bash
python --version
node --version
npm --version
```

---

## Project Structure

```
Intpt-Webdev/
├── flask_backend/          # Flask backend + Tailwind CSS
│   ├── app/
│   ├── static/
│   ├── templates/
│   ├── services/
│   ├── run.py             # Flask entry point
│   ├── app.py             # Flask app initialization
│   └── requirements.txt   # Python dependencies
├── supabase/              # Supabase configuration
├── Md/                    # Documentation
└── package.json           # Root npm config
```

---

## Setup Instructions

### Step 1: Clone the Repository

```bash
cd Documents
git clone https://github.com/ZeroObjectivo/Intpt-Webdev.git
cd Intpt-Webdev
```

### Step 2: Set Up Python Virtual Environment

Navigate to the flask_backend directory and create a virtual environment:

```bash
cd flask_backend
python -m venv venv
```

**Activate the virtual environment:**

**On Windows (PowerShell):**
```powershell
.\venv\Scripts\Activate
```

**On Windows (Command Prompt):**
```cmd
venv\Scripts\activate
```

**On macOS/Linux:**
```bash
source venv/bin/activate
```

### Step 3: Install Python Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Configure Environment Variables

Create a `.env` file in the `flask_backend/` directory with the following:

```env
SECRET_KEY=your-secret-key-here
FLASK_ENV=development
FLASK_DEBUG=True
SUPABASE_URL=your-supabase-url
SUPABASE_KEY=your-supabase-key
SUPABASE_SERVICE_ROLE_KEY=your-supabase-service-role-key
```

**Get your Supabase credentials:**
1. Go to [Supabase Dashboard](https://app.supabase.com/)
2. Select your project
3. Navigate to **Settings** → **API**
4. Copy the `URL` and `anon` public key
5. Copy the `service_role` key for admin operations (keep this server-side only)

### Step 5: Install Node.js Dependencies

Install frontend dependencies for Tailwind CSS:

```bash
npm install
```

This installs:
- `tailwindcss` - CSS utility framework
- `autoprefixer` - CSS vendor prefixing
- `postcss` - CSS processing

---

## Running the Application

### **Option 1: Run Both Services in Separate Terminals (Recommended)**

You need **two terminal windows/tabs** running simultaneously:

#### Terminal 1: Flask Backend Server

```bash
cd flask_backend
# Activate virtual environment first (if not already activated)
# On Windows: .\venv\Scripts\Activate
# On macOS/Linux: source venv/bin/activate

python run.py
```

**Expected output:**
```
 * Serving Flask app 'app'
 * Debug mode: on
 * Running on http://127.0.0.1:5000
```

The Flask server will run on `http://localhost:5000`

#### Terminal 2: Tailwind CSS Watcher

```bash
cd flask_backend
npm run dev
```

**Expected output:**
```
Rebuilding...
input.css and output.css now have the same content
Watching for changes...
```

This continuously compiles your CSS as you make changes.

### **Option 2: Run Tailwind Build Only (Production-like)**

If you don't need live CSS editing, build Tailwind once:

```bash
cd flask_backend
npm run build
```

Then run only the Flask server:

```bash
python run.py
```

---

## Accessing the Application

Once both services are running:

- **Main App:** Open http://localhost:5000 in your browser
- **Login Page:** http://localhost:5000/login
- **Dashboard:** http://localhost:5000/dashboard (after login)

---

## Stopping the Application

### Stop the Flask Server
- Press **Ctrl+C** in the Flask terminal
- Wait for the server to shut down gracefully

### Stop the Tailwind Watcher
- Press **Ctrl+C** in the npm terminal
- The process will terminate immediately

### Deactivate Virtual Environment
```bash
deactivate
```

---

## Common Issues & Troubleshooting

### Issue 1: Port 5000 Already in Use

**Error:** `OSError: [Errno 48] Address already in use`

**Solution:**
```bash
# Find process using port 5000
netstat -ano | findstr :5000

# Kill the process (Windows)
taskkill /PID <PID> /F

# Or change Flask port in run.py:
app.run(debug=True, port=5001)
```

### Issue 2: Virtual Environment Not Activating

**Solution:** Use the full path:
```bash
& ".\venv\Scripts\Activate.ps1"
```

### Issue 3: npm run dev fails

**Solution:** Ensure you're in the `flask_backend/` directory:
```bash
cd flask_backend
npm install  # Reinstall if needed
npm run dev
```

### Issue 4: Missing Dependencies

**Solution:** Reinstall all dependencies:
```bash
# Python
pip install --upgrade pip
pip install -r requirements.txt

# Node
npm ci  # Clean install
```

### Issue 5: Supabase Connection Fails

**Solution:** Check your `.env` file:
```bash
# Verify environment variables are set correctly
cat .env
```

---

## Development Workflow

### Making Changes to CSS/Tailwind

1. Edit files in `app/static/css/input.css`
2. The `npm run dev` watcher automatically compiles to `app/static/css/style.css`
3. Refresh your browser to see changes

### Making Changes to Python/Flask

1. Edit files in `app/` directory
2. Flask's debug mode automatically reloads the server
3. Refresh your browser to see changes

### Adding New Dependencies

**Python:**
```bash
pip install package-name
pip freeze > requirements.txt
```

**Node.js:**
```bash
npm install package-name
npm install --save-dev package-name  # For dev dependencies
```

---

## Database Management (Supabase)

### Run Migrations

```bash
supabase migration up
```

### View Database Changes

1. Go to [Supabase Dashboard](https://app.supabase.com/)
2. Select your project
3. Navigate to **SQL Editor** to view tables

---

## Deployment

For production deployment, see [Execution.md](./Md/Execution.md) and the project architecture documentation.

---

## Quick Reference

| Task | Command |
|------|---------|
| Activate venv (Windows) | `.\venv\Scripts\Activate` |
| Activate venv (macOS/Linux) | `source venv/bin/activate` |
| Install Python deps | `pip install -r requirements.txt` |
| Install Node deps | `npm install` |
| Run Flask server | `python run.py` |
| Watch Tailwind CSS | `npm run dev` |
| Build Tailwind CSS | `npm run build` |
| Stop server | `Ctrl+C` |
| Deactivate venv | `deactivate` |

---

## Need Help?

- Check [ProjectPlan.md](./Md/ProjectPlan.md) for feature overview
- Check [DESIGN.md](./Md/DESIGN.md) for design system
- Review [Execution.md](./Md/Execution.md) for architecture details
- Check Flask documentation: https://flask.palletsprojects.com/
- Check Tailwind documentation: https://tailwindcss.com/
