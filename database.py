import os
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Set, Tuple, Any, Optional

# DB file at the same directory as script
DB_PATH = os.environ.get(
    'DB_PATH',
    os.path.join(os.path.dirname(os.path.abspath(__file__)), 'movies.db')
)

def get_connection() -> sqlite3.Connection:
    """
    Establishes and returns a database connection with sqlite3.Row row factory.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db() -> None:
    """
    Creates all the tables needed for the Movie Mood Analyzer application:
    - watched_movies: id, imdb_id (unique), title, year, poster, genre, rating, plot, watched_at
    - watchlist: id, imdb_id (unique), title, year, poster, genre, rating, plot, added_at
    - mood_sessions: id, mood, created_at
    """
    conn = get_connection()
    try:
        with conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT UNIQUE NOT NULL,
                    display_name TEXT NOT NULL,
                    password_hash TEXT,
                    created_at TEXT DEFAULT (datetime('now', 'localtime'))
                )
            ''')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS magic_login_tokens (
                    token_hash TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    expires_at TEXT NOT NULL,
                    created_at TEXT DEFAULT (datetime('now', 'localtime')),
                    used_at TEXT
                )
            ''')
            _ensure_owned_movie_table(conn, 'watched_movies', 'watched_at')
            _ensure_owned_movie_table(conn, 'watchlist', 'added_at')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS mood_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    mood TEXT,
                    created_at TEXT DEFAULT (datetime('now', 'localtime')),
                    user_id INTEGER REFERENCES users(id)
                )
            ''')
            mood_columns = {row['name'] for row in conn.execute('PRAGMA table_info(mood_sessions)')}
            if 'user_id' not in mood_columns:
                conn.execute('ALTER TABLE mood_sessions ADD COLUMN user_id INTEGER REFERENCES users(id)')
            for table in ('watched_movies', 'watchlist'):
                conn.execute(
                    f'CREATE UNIQUE INDEX IF NOT EXISTS idx_{table}_owner_movie '
                    f'ON {table}(COALESCE(user_id, 0), imdb_id)'
                )
    finally:
        conn.close()

def _ensure_owned_movie_table(conn: sqlite3.Connection, table: str, date_column: str) -> None:
    """Rebuild legacy global-unique movie tables with owner-scoped uniqueness."""
    columns = {row['name'] for row in conn.execute(f'PRAGMA table_info({table})')}
    if not columns:
        conn.execute(f'''
            CREATE TABLE {table} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                imdb_id TEXT NOT NULL,
                title TEXT,
                year TEXT,
                poster TEXT,
                genre TEXT,
                rating TEXT,
                plot TEXT,
                {date_column} TEXT DEFAULT (datetime('now', 'localtime')),
                user_id INTEGER REFERENCES users(id)
            )
        ''')
        return

    unique_movie_only = any(
        index['unique'] and [
            column['name']
            for column in conn.execute(f"PRAGMA index_info('{index['name']}')")
        ] == ['imdb_id']
        for index in conn.execute(f'PRAGMA index_list({table})')
    )
    if 'user_id' not in columns or unique_movie_only:
        legacy_table = f'{table}_legacy_migration'
        conn.execute(f'DROP TABLE IF EXISTS {legacy_table}')
        conn.execute(f'ALTER TABLE {table} RENAME TO {legacy_table}')
        _ensure_owned_movie_table(conn, table, date_column)
        legacy_columns = {row['name'] for row in conn.execute(f'PRAGMA table_info({legacy_table})')}
        copy_columns = ['id', 'imdb_id', 'title', 'year', 'poster', 'genre', 'rating', 'plot', date_column]
        select_columns = [column if column in legacy_columns else 'NULL' for column in copy_columns]
        owner_column = 'user_id' if 'user_id' in legacy_columns else 'NULL'
        conn.execute(
            f'INSERT INTO {table} ({", ".join(copy_columns)}, user_id) '
            f'SELECT {", ".join(select_columns)}, {owner_column} FROM {legacy_table}'
        )
        conn.execute(f'DROP TABLE {legacy_table}')

def create_account(email: str, display_name: str, password_hash: Optional[str]) -> Dict[str, Any]:
    conn = get_connection()
    try:
        with conn:
            is_first_account = conn.execute('SELECT 1 FROM users LIMIT 1').fetchone() is None
            cursor = conn.execute(
                'INSERT INTO users (email, display_name, password_hash) VALUES (?, ?, ?)',
                (email, display_name, password_hash)
            )
            user_id = cursor.lastrowid
            if is_first_account:
                conn.execute('UPDATE watched_movies SET user_id = ? WHERE user_id IS NULL', (user_id,))
                conn.execute('UPDATE watchlist SET user_id = ? WHERE user_id IS NULL', (user_id,))
                conn.execute('UPDATE mood_sessions SET user_id = ? WHERE user_id IS NULL', (user_id,))
        return {'id': user_id, 'email': email, 'display_name': display_name}
    finally:
        conn.close()

def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    try:
        row = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()

def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    try:
        row = conn.execute(
            'SELECT id, email, display_name FROM users WHERE id = ?', (user_id,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()

def create_magic_token(token_hash: str, user_id: int) -> bool:
    conn = get_connection()
    try:
        with conn:
            recent = conn.execute('''
                SELECT COUNT(*) FROM magic_login_tokens
                WHERE user_id = ? AND created_at >= datetime('now', '-15 minutes')
            ''', (user_id,)).fetchone()[0]
            if recent >= 5:
                return False
            expires_at = (datetime.now() + timedelta(minutes=15)).strftime('%Y-%m-%d %H:%M:%S')
            conn.execute(
                'INSERT INTO magic_login_tokens (token_hash, user_id, expires_at) VALUES (?, ?, ?)',
                (token_hash, user_id, expires_at)
            )
        return True
    finally:
        conn.close()

def consume_magic_token(token_hash: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    try:
        with conn:
            row = conn.execute('''
                SELECT users.id, users.email, users.display_name
                FROM magic_login_tokens
                JOIN users ON users.id = magic_login_tokens.user_id
                WHERE token_hash = ? AND used_at IS NULL AND expires_at > datetime('now', 'localtime')
            ''', (token_hash,)).fetchone()
            if not row:
                return None
            conn.execute(
                "UPDATE magic_login_tokens SET used_at = datetime('now', 'localtime') WHERE token_hash = ?",
                (token_hash,)
            )
            return dict(row)
    finally:
        conn.close()

def mark_watched(movie_dict: Dict[str, Any], user_id: Optional[int] = None) -> None:
    """
    Marks a movie as watched:
    1. Inserts or updates the movie in the watched_movies table.
    2. Deletes the movie from the watchlist table (if it exists).
    """
    imdb_id = movie_dict.get('imdb_id')
    if not imdb_id:
        raise ValueError("movie_dict must contain a valid 'imdb_id'")

    conn = get_connection()
    try:
        with conn:
            keys = ['imdb_id', 'title', 'year', 'poster', 'genre', 'rating', 'plot', 'user_id']
            vals = [movie_dict.get(k) for k in keys[:-1]] + [user_id]
            
            watched_at = movie_dict.get('watched_at')
            if watched_at:
                keys.append('watched_at')
                vals.append(watched_at)
                
            placeholders = ', '.join(['?'] * len(vals))
            columns = ', '.join(keys)
            
            conn.execute(f"INSERT OR REPLACE INTO watched_movies ({columns}) VALUES ({placeholders})", vals)
            conn.execute('DELETE FROM watchlist WHERE imdb_id = ? AND user_id IS ?', (imdb_id, user_id))
    finally:
        conn.close()

def get_watched_ids(user_id: Optional[int] = None) -> Set[str]:
    """
    Returns a set of imdb_ids of all watched movies.
    """
    conn = get_connection()
    try:
        cursor = conn.execute('SELECT imdb_id FROM watched_movies WHERE user_id IS ?', (user_id,))
        return {row['imdb_id'] for row in cursor.fetchall()}
    finally:
        conn.close()

def get_watched_movies(user_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Returns all watched movies as a list of dictionaries.
    """
    conn = get_connection()
    try:
        cursor = conn.execute('SELECT * FROM watched_movies WHERE user_id IS ? ORDER BY watched_at DESC', (user_id,))
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()

def add_to_watchlist(movie_dict: Dict[str, Any], user_id: Optional[int] = None) -> Tuple[bool, str]:
    """
    Adds a movie to the watchlist.
    Skips if the movie has already been watched.
    Returns (True, success_message) or (False, error_message).
    """
    imdb_id = movie_dict.get('imdb_id')
    if not imdb_id:
        return False, "imdb_id is required"

    if imdb_id in get_watched_ids(user_id):
        return False, "Movie has already been watched"

    conn = get_connection()
    try:
        with conn:
            keys = ['imdb_id', 'title', 'year', 'poster', 'genre', 'rating', 'plot', 'user_id']
            vals = [movie_dict.get(k) for k in keys[:-1]] + [user_id]
            
            added_at = movie_dict.get('added_at')
            if added_at:
                keys.append('added_at')
                vals.append(added_at)
                
            placeholders = ', '.join(['?'] * len(vals))
            columns = ', '.join(keys)
            
            conn.execute(f"INSERT INTO watchlist ({columns}) VALUES ({placeholders})", vals)
        return True, "Movie added to watchlist successfully"
    except sqlite3.IntegrityError:
        return False, "Movie is already in the watchlist"
    finally:
        conn.close()

def get_watchlist(user_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Returns all movies in the watchlist as a list of dictionaries.
    """
    conn = get_connection()
    try:
        cursor = conn.execute('SELECT * FROM watchlist WHERE user_id IS ? ORDER BY added_at DESC', (user_id,))
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()

def remove_from_watchlist(imdb_id: str, user_id: Optional[int] = None) -> None:
    """
    Removes a movie from the watchlist by its imdb_id.
    """
    conn = get_connection()
    try:
        with conn:
            conn.execute('DELETE FROM watchlist WHERE imdb_id = ? AND user_id IS ?', (imdb_id, user_id))
    finally:
        conn.close()

def log_mood(mood_string: str, user_id: Optional[int] = None) -> None:
    """
    Logs a mood session into the database.
    """
    conn = get_connection()
    try:
        with conn:
            conn.execute('INSERT INTO mood_sessions (mood, user_id) VALUES (?, ?)', (mood_string, user_id))
    finally:
        conn.close()

def get_stats(user_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Returns a dictionary containing statistics:
    - watched_count: total watched movies
    - watchlist_count: total movies in watchlist
    - top_mood: most frequent mood session, or None if none exist
    """
    conn = get_connection()
    try:
        watched_row = conn.execute('SELECT COUNT(*) FROM watched_movies WHERE user_id IS ?', (user_id,)).fetchone()
        watchlist_row = conn.execute('SELECT COUNT(*) FROM watchlist WHERE user_id IS ?', (user_id,)).fetchone()
        
        watched_count = watched_row[0] if watched_row else 0
        watchlist_count = watchlist_row[0] if watchlist_row else 0

        # Retrieve top mood
        # Group by mood and find the one with the highest count.
        # Break ties by id DESC to get the latest mood.
        top_mood_row = conn.execute('''
            SELECT mood 
            FROM mood_sessions
            WHERE user_id IS ?
            GROUP BY mood 
            ORDER BY COUNT(*) DESC, id DESC 
            LIMIT 1
        ''', (user_id,)).fetchone()
        
        top_mood = top_mood_row[0] if top_mood_row else None

        return {
            'watched_count': watched_count,
            'watchlist_count': watchlist_count,
            'top_mood': top_mood
        }
    finally:
        conn.close()

def get_analytics_data(user_id: Optional[int] = None) -> Dict[str, Any]:
    """Return compact aggregates used by the React analytics charts."""
    conn = get_connection()
    try:
        mood_rows = conn.execute('''
            SELECT mood, COUNT(*) AS count
            FROM mood_sessions
            WHERE mood IS NOT NULL AND user_id IS ?
            GROUP BY mood
            ORDER BY count DESC, mood
        ''', (user_id,)).fetchall()
        watched_rows = conn.execute('SELECT genre FROM watched_movies WHERE genre IS NOT NULL AND user_id IS ?', (user_id,)).fetchall()
        monthly_rows = conn.execute('''
            SELECT strftime('%Y-%m', watched_at) AS month, COUNT(*) AS count
            FROM watched_movies
            WHERE watched_at IS NOT NULL AND user_id IS ?
            GROUP BY month
            ORDER BY month
        ''', (user_id,)).fetchall()
        rating_row = conn.execute('''
            SELECT AVG(CAST(rating AS REAL))
            FROM watched_movies
            WHERE rating GLOB '[0-9]*' AND user_id IS ?
        ''', (user_id,)).fetchone()

        genre_counts: Dict[str, int] = {}
        for row in watched_rows:
            for genre in (row['genre'] or '').split(','):
                normalized = genre.strip()
                if normalized and normalized != 'N/A':
                    genre_counts[normalized] = genre_counts.get(normalized, 0) + 1

        return {
            'mood_counts': [{'mood': row['mood'], 'count': row['count']} for row in mood_rows],
            'genre_counts': [
                {'genre': genre, 'count': count}
                for genre, count in sorted(genre_counts.items(), key=lambda item: (-item[1], item[0]))[:8]
            ],
            'monthly_watches': [
                {'month': row['month'], 'count': row['count']}
                for row in monthly_rows if row['month']
            ],
            'average_rating': round(rating_row[0], 1) if rating_row and rating_row[0] is not None else None
        }
    finally:
        conn.close()
