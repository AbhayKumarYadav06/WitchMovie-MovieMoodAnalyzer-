# WitchMovie | Movie Mood Analyzer

A React movie companion that recommends films for eight different moods. WitchMovie combines OMDb search and movie details with private, account-based SQLite watch history, watchlists, and live viewing insights. Sign in with an email and password or request a one-time email link.

---

## 1. Project Structure

The React interface is in `frontend/`; run it with Vite for development or build it into `dist/` for Flask to serve. Flask owns account authentication, signed sessions, and private data access.

```text
mma/
├── frontend/               # WitchMovie React application and custom logo
├── auth.py                 # Password hashing, magic-link tokens, and SMTP delivery
├── requirements.txt        # Python dependencies
├── package.json            # React, Vite, Recharts, and icon dependencies
├── database.py             # SQLite persistence routines for storing watch history, watchlist, and mood sessions
├── omdb.py                 # OMDB API integration, mood profile configurations, and recommendation query logic
├── app.py                  # Flask REST API server exposing backend operations to the frontend on port 5000
├── test_database.py        # Unit test suite verifying database table routines, insertions, and constraints
├── test_omdb.py            # Unit test suite verifying OMDB search and detail mocks
├── test_app.py             # Unit test suite verifying all Flask REST API routes
└── README.md               # Project documentation (this file)
```

---

## 2. Setup & Installation

### Step 1: Install Dependencies

Install the Python and frontend dependencies:

```bash
pip install -r requirements.txt
npm install
```

### Step 2: Configure OMDB API Key

Set the OMDb API key as an environment variable. In Windows PowerShell, run this in the backend terminal:

```powershell
$env:OMDB_API_KEY="your_key"
$env:SECRET_KEY="a-long-random-secret-for-flask-sessions"
```

Use a unique, persistent `SECRET_KEY` for any deployment so sessions remain valid after restarts. For HTTPS deployments, set `$env:FORCE_SECURE_COOKIES="1"`. For email sign-in links, configure `SMTP_HOST`, `SMTP_PORT` (default `587`), `SMTP_USER`, `SMTP_PASSWORD`, and `SMTP_FROM`. For an SSL SMTP service on port 465, also set `$env:SMTP_USE_SSL="1"`. Set `APP_BASE_URL` to the public WitchMovie URL when deploying. To test the sign-in link without SMTP on a local machine, explicitly set `$env:AUTH_DEV_MODE="1"`; this mode returns the short-lived link in the API response and must not be enabled in production.

### Step 3: Start the Flask API

In a terminal, start the backend:

```bash
python app.py
```

_Note: This automatically initializes the SQLite database file (`movies.db`) in the same directory._

### Step 4: Start the React app

In a second terminal:

```bash
npm run dev
```

Open `http://localhost:5173`. Vite proxies `/api` requests to Flask on port 5000.

### Expo / production build

Build the React app and then run Flask. Flask serves the built website at `http://localhost:5000`:

```bash
npm run build
python app.py
```

### Host WitchMovie on Render

Deploy this as one **Web Service** so Flask serves both the React site and its `/api` routes. Do not use a static-site-only service: sign-in and movie data require the Flask API.

1. Push the project to a GitHub repository, then create a Render Web Service connected to that repository.
2. Set the build command to `pip install -r requirements.txt && npm install && npm run build`.
3. Set the start command to `gunicorn app:app`.
4. Attach a persistent disk mounted at `/var/data`. Set `DB_PATH` to `/var/data/movies.db`; without persistent storage, SQLite account and collection data can be lost when the service is replaced.
5. Add environment variables in the Render service settings:

| Variable                                                            | Value                                                                |
| :------------------------------------------------------------------ | :------------------------------------------------------------------- |
| `OMDB_API_KEY`                                                      | Your OMDb API key                                                    |
| `SECRET_KEY`                                                        | A long, random, private value that stays the same between deploys    |
| `DB_PATH`                                                           | `/var/data/movies.db`                                                |
| `FORCE_SECURE_COOKIES`                                              | `1`                                                                  |
| `APP_BASE_URL`                                                      | Your deployed HTTPS URL, such as `https://your-service.onrender.com` |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM` | Your email provider's SMTP settings, required for email-link sign-in |

Leave `AUTH_DEV_MODE` unset in production. It returns a sign-in token in the API response and is only for local testing. After deployment, open the service URL, create an account, and verify both password and email-link sign-in. Keep the service and persistent disk in the same region; persistent disks may require a paid hosting plan.

---

## 3. Features

| Feature                   | Description                                                                                                                                     |
| :------------------------ | :---------------------------------------------------------------------------------------------------------------------------------------------- |
| **Mood Recommendations**  | Recommends films for 8 moods and optionally filters by Hollywood, Tollywood, Ollywood, Bollywood, animation, anime, Korean, or Japanese cinema. |
| **Smart Filtering**       | Automatically filters recommendations to skip previously watched items and duplicates, and reports the count of excluded movies.                |
| **Real-time Search**      | Performs dynamic query searches against the OMDB database with visual indicators for already watched movies.                                    |
| **Watch Tracking**        | Easily marks movies as watched, updating the local database and dynamically adjusting visual states across the app.                             |
| **Watchlist Management**  | Saves desired movies for later and automatically moves them to history upon being watched.                                                      |
| **Detail Modal**          | Opens a comprehensive detail overlay with plot synopses, cast lists, runtime indicators, and rating pills (IMDb, Metacritic, Rotten Tomatoes).  |
| **Statistics & Insights** | Shows watched and saved totals, your top mood, average rating, mood distribution, most-watched genres, and monthly viewing activity.            |
| **Responsive React UI**   | React + Vite interface with custom Witch branding, responsive navigation, and interactive Recharts visualizations.                              |
| **Private movie club**    | Email/password accounts, signed sessions, passwordless email links, and separate watch history, mood insights, and watchlists per account.      |

## 4. REST API Endpoints

All endpoints are hosted under `http://localhost:5000/api`.

| Method   | Endpoint                                               | Description                                                                                                                                     |
| :------- | :----------------------------------------------------- | :---------------------------------------------------------------------------------------------------------------------------------------------- |
| `POST`   | `/api/auth/signup`                                     | Create an account with display name, email, and a password of at least 10 characters.                                                           |
| `POST`   | `/api/auth/login`                                      | Sign in using email and password.                                                                                                               |
| `POST`   | `/api/auth/magic-link`                                 | Email a one-time sign-in link to an existing account (15-minute expiry).                                                                        |
| `POST`   | `/api/auth/verify`                                     | Verify and consume a one-time sign-in token.                                                                                                    |
| `GET`    | `/api/auth/me`                                         | Restore the current signed-in account.                                                                                                          |
| `POST`   | `/api/auth/logout`                                     | End the current session.                                                                                                                        |
| `GET`    | `/api/moods`                                           | Returns configurations (name, label, color, description) of the 8 available moods.                                                              |
| `GET`    | `/api/recommend?mood=X&industries=tollywood,animation` | Logs the mood and returns recommendations, profile, and excluded count. The optional comma-separated `industries` filter defaults to all films. |
| `GET`    | `/api/search?q=X&page=N`                               | Searches movies from OMDB by title, returning list results and adding an `is_watched` boolean to each movie dict.                               |
| `GET`    | `/api/movie/<imdb_id>`                                 | Returns full details of a specific movie, including its `is_watched` status.                                                                    |
| `GET`    | `/api/watched`                                         | Returns all movies from the watched history database.                                                                                           |
| `POST`   | `/api/watched`                                         | Accepts a movie dict (supports `imdbID` / `imdb_id` keys) and inserts it into watched history (removing it from watchlist if present).          |
| `DELETE` | `/api/watched/<imdb_id>`                               | Deletes a movie from the watched history.                                                                                                       |
| `GET`    | `/api/watchlist`                                       | Returns all movies on the user's watchlist.                                                                                                     |
| `POST`   | `/api/watchlist`                                       | Adds a movie to the watchlist. Returns `400` if already watched.                                                                                |
| `DELETE` | `/api/watchlist/<imdb_id>`                             | Removes a movie from the watchlist.                                                                                                             |
| `GET`    | `/api/stats`                                           | Returns general metrics (watched count, watchlist count, and top mood).                                                                         |
| `GET`    | `/api/analytics/data`                                  | Returns mood, genre, monthly-watch, and average-rating aggregates for the frontend charts.                                                      |

---

## 5. Database Schema

The database uses SQLite. Tables are initialized automatically upon backend server launch:

```sql
-- Watched History
CREATE TABLE IF NOT EXISTS watched_movies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    imdb_id TEXT UNIQUE NOT NULL,
    title TEXT,
    year TEXT,
    poster TEXT,
    genre TEXT,
    rating TEXT,
    plot TEXT,
    watched_at TEXT DEFAULT (datetime('now', 'localtime'))
);

-- Watchlist
CREATE TABLE IF NOT EXISTS watchlist (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    imdb_id TEXT UNIQUE NOT NULL,
    title TEXT,
    year TEXT,
    poster TEXT,
    genre TEXT,
    rating TEXT,
    plot TEXT,
    added_at TEXT DEFAULT (datetime('now', 'localtime'))
);

-- Mood Sessions History
CREATE TABLE IF NOT EXISTS mood_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    mood TEXT,
    created_at TEXT DEFAULT (datetime('now', 'localtime'))
);
```
