# Headlamp Backend

Minimal FastAPI starter using a routes → services → repos pattern with optional Supabase integration.

## Setup

1. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

2. Create a `.env` file and set any secrets:

   ```
   SUPABASE_URL=
   SUPABASE_KEY=
   APP_NAME=Headlamp API
   DEBUG=False
   ```

3. Run the development server:
   ```bash
   uvicorn main:app --reload
   ```

## Structure

- `routes/health.py` — FastAPI router exposing the `/api/health` endpoint
- `services/health.py` — thin service layer helpers (function-based)
- `repos/supabase.py` — accessor for the Supabase client (cached)
- `models/health.py` — response model definitions
- `config.py` — environment-driven application configuration
- `main.py` — FastAPI application entry point

Extend the pattern by adding more routes, pairing each with small service helpers and repository functions as needed.
