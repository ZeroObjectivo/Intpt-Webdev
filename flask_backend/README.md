# University Social Platform - Herons Hub (Flask Version)

A modern, responsive social platform for the University of Makati community, built with **Flask**, **Supabase**, and **Tailwind CSS**. This project translates high-fidelity Figma designs into a modular, scalable web application.

## 🚀 Features

- **Google OAuth Integration:** Secure login restricted to `@umak.edu.ph` email addresses via Supabase Auth.
- **Real-time Backend:** Leveraging Supabase for authentication and database management.
- **Modular Architecture:** Organized folder structure using Flask Blueprints and dedicated services.
- **Modern UI:** Responsive design based on Figma specifications.
- **Tailwind CSS Integration:** Full JIT compilation workflow for optimized styles.
- **Brand Identity:** Customized with University of Makati colors and official assets.

## 🛠️ Technical Stack

- **Backend:** Flask 3.1+
- **Database & Auth:** Supabase (PostgreSQL + Supabase Auth)
- **Frontend:** Tailwind CSS 3.4+
- **Environment:** Python 3.14+, Node.js (for Tailwind CLI)

## 📂 Project Structure

```text
flask_backend/
├── app/                 # Main application package
│   ├── routes/          # Flask Blueprints for auth and core logic
│   ├── static/          # Static assets (compiled CSS, JS, Images)
│   ├── templates/       # HTML templates (Jinja2)
│   │   └── includes/    # Reusable template partials
│   └── __init__.py      # App factory
├── services/            # External service integrations (Supabase Client)
├── tailwind.config.js   # Tailwind CSS configuration
├── package.json         # Frontend build scripts
├── requirements.txt     # Python dependencies
├── .env                 # Environment variables (Configuration)
└── run.py               # Entry point to run the server
```

## 🏁 Getting Started

### Prerequisites

1.  **Python 3.14+**
2.  **Node.js & npm** (for Tailwind CSS development)
3.  **Supabase Account** (to host the database and authentication)

### Installation & Setup

1.  **Navigate to the project directory:**
    ```bash
    cd flask_backend
    ```

2.  **Create and activate a virtual environment:**
    ```bash
    python -m venv venv
    # Windows:
    .\venv\Scripts\activate
    # macOS/Linux:
    source venv/bin/activate
    ```

3.  **Install Python Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Install Frontend Dependencies:**
    ```bash
    npm install
    ```

5.  **Configure Environment Variables:**
    Create a `.env` file in the `flask_backend/` root:
    ```env
    SUPABASE_URL=your_supabase_project_url
    SUPABASE_KEY=your_supabase_anon_key
    DATABASE_URL=your_postgresql_connection_string
    SECRET_KEY=your_flask_secret_key
    ```

### Running the Project

To run the project properly, you need to manage both the Flask server and the Tailwind CSS compiler.

#### 1. Compile Tailwind CSS
In one terminal, run the following to build the CSS and watch for changes:
```bash
npm run dev
```

#### 2. Start Flask Server
In a second terminal, ensure your virtual environment is active and start the development server:
```bash
python run.py
```

Open your browser and navigate to `http://127.0.0.1:5000/`.

---

## 🎨 Design Reference
The UI is built to match the provided Figma designs, utilizing the official university assets.
