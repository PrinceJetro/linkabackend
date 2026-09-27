# 🌍 Linka Backend

The backend engine powering Linka — Africa's B2B partnership network. Built with Django and Django REST Framework, it handles authentication, capability profiles, partnership matching logic, intent broadcasts, and integrations with the Gemini API for semantic matching and AI-generated MOUs.

## 🚀 Tech Stack

- **Framework**: Django 5.1 + Django REST Framework
- **Database**: PostgreSQL (via Supabase) / SQLite (local fallback)
- **AI Integration**: Google Gemini API (`google-genai`)
- **Deployment**: Vercel Serverless

## ⚙️ Prerequisites

- Python 3.10+
- `pip` and `virtualenv`

## 🛠️ Local Setup

1. **Create and activate a virtual environment:**
   ```bash
   python -m venv env
   # On Windows:
   env\Scripts\activate
   # On macOS/Linux:
   source env/bin/activate
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Environment Variables:**
   Create a `.env` file in the root of the backend directory (`backend/linka/.env`). Ask a team member for the database credentials or use SQLite locally by leaving the DB vars blank.

   ```env
   # Core
   DJANGO_SECRET_KEY="your-secret-key"
   DJANGO_DEBUG="True"
   
   # Database (PostgreSQL)
   DB_HOST="your-supabase-host"
   DB_PORT="5432" # or 6543
   DB_NAME="postgres"
   DB_USER="your-db-user"
   DB_PASSWORD="your-db-password"
   
   # AI Features
   GEMINI_API_KEY="your-gemini-key"
   ```

4. **Run migrations:**
   ```bash
   python manage.py migrate
   ```

5. **Start the development server:**
   ```bash
   python manage.py runserver
   ```
   The API will be available at `http://127.0.0.1:8000/`.

## 🌱 Seeding Demo Data

For testing the UI with realistic profiles across Africa (Nigeria, Ghana, Kenya, Rwanda, South Africa), use the seed script:

```bash
python seed_demo.py
```

This will create an array of profiles and a `demo` account (Password: `demo12345`) that you can log into on the frontend.

## 🏗️ Project Structure

- `api/` - API routing and Vercel serverless entrypoint
- `linka/` - Core Django settings and WSGI/ASGI configurations
- `profiles/` - Main app containing models and API views for Users, Profiles, Requests, Messages, and Broadcasts
- `seed_demo.py` - Script to populate the database with hackathon mock data
- `requirements.txt` - Python dependencies (mirrored in `backend/` for Vercel)

## 🚢 Deployment

This backend is configured for deployment on **Vercel**.
- Set the Root Directory to `backend/linka` (or `backend` depending on your exact Vercel setup).
- The `vercel.json` and `api/index.py` handle routing the WSGI application to Vercel's serverless functions.
- Ensure all environment variables are added to the Vercel project settings.
