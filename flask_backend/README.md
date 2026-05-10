# University Social Platform - UniSocial (Flask Version)

A modern, responsive social platform for the University of Makati community, built with **Flask** and **Tailwind CSS**. This project translates high-fidelity Figma designs into a modular, scalable web application.

## 🚀 Features

- **Modular Architecture:** Organized folder structure using Flask Blueprints.
- **Modern UI:** Responsive design based on Figma specifications.
- **Tailwind CSS Integration:** Full JIT compilation workflow for optimized styles.
- **Reusable Components:** Modular Jinja2 templates (Navbar, Footer, Hero, Cards).
- **Brand Identity:** Customized with University of Makati colors and official assets.

## 🛠️ Technical Stack

- **Backend:** Flask 3.1+
- **Frontend:** Tailwind CSS 3.4+
- **Environment:** Python 3.14+, Node.js (for Tailwind CLI)

## 📂 Project Structure

```text
flask_backend/
├── app/                 # Main application package
│   ├── static/          # Static assets (compiled CSS, JS, Images)
│   ├── templates/       # HTML templates
│   │   └── includes/    # Reusable template partials
│   ├── __init__.py      # App factory
│   └── routes.py        # Blueprints and routing
├── tailwind.config.js   # Tailwind CSS configuration
├── package.json        # Frontend build scripts
└── run.py              # Entry point to run the server
```

## 🏁 Getting Started

### Prerequisites

1.  **Python 3.14+**
2.  **Node.js & npm** (for Tailwind CSS development)

### Installation & Setup

1.  **Navigate to the project directory:**
    ```bash
    cd flask_backend
    ```

2.  **Install Flask:**
    ```bash
    pip install flask
    ```

3.  **Install Frontend Dependencies:**
    ```bash
    npm install
    ```

### Running the Project

To run the project properly, you need to manage both the Flask server and the Tailwind CSS compiler.

#### 1. Compile Tailwind CSS
In one terminal, run the following to build the CSS and watch for changes:
```bash
npm run dev
```

#### 2. Start Flask Server
In a second terminal, start the development server:
```bash
python run.py
```

Open your browser and navigate to `http://127.0.0.1:5000/`.

---

## 🎨 Design Reference
The UI is built to match the provided Figma designs, utilizing the official university assets.
