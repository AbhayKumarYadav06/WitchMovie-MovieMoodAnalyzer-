import os
import re
import secrets
import smtplib
from datetime import timedelta
from flask import Flask, request, jsonify, send_file, send_from_directory, session, g
from flask_cors import CORS
import database as db
import omdb
import auth as auth_service

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY') or secrets.token_hex(32)
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    SESSION_COOKIE_SECURE=os.environ.get('FORCE_SECURE_COOKIES') == '1',
    PERMANENT_SESSION_LIFETIME=timedelta(days=14),
)
# Enable CORS for all routes and origins
CORS(app)

# Initialize database tables on startup
db.init_db()

@app.before_request
def require_account_for_private_api():
    if not request.path.startswith('/api/'):
        return None
    if request.path == '/api/moods' or request.path.startswith('/api/auth/'):
        return None
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Sign in to use your WitchMovie account.'}), 401
    g.user_id = user_id
    return None

def current_user_id():
    return g.user_id

def public_user(user):
    return {'id': user['id'], 'email': user['email'], 'display_name': user['display_name']}

@app.route('/api/auth/me', methods=['GET'])
def auth_me():
    user_id = session.get('user_id')
    user = db.get_user_by_id(user_id) if user_id else None
    if not user:
        session.clear()
        return jsonify({'user': None})
    return jsonify({'user': public_user(user)})

@app.route('/api/auth/signup', methods=['POST'])
def auth_signup():
    payload = request.get_json(silent=True) or {}
    email = auth_service.normalize_email(str(payload.get('email', '')))
    display_name = str(payload.get('display_name', '')).strip()
    password = str(payload.get('password', ''))
    if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', email):
        return jsonify({'error': 'Enter a valid email address.'}), 400
    if not display_name or len(display_name) > 60:
        return jsonify({'error': 'Enter a name up to 60 characters.'}), 400
    if len(password) < 10:
        return jsonify({'error': 'Use a password with at least 10 characters.'}), 400
    if db.get_user_by_email(email):
        return jsonify({'error': 'An account already exists for this email. Sign in instead.'}), 409
    try:
        user = auth_service.create_account(email, display_name, password)
    except Exception:
        app.logger.exception('Account creation failed')
        return jsonify({'error': 'Could not create your account. Please try again.'}), 500
    session.clear()
    session['user_id'] = user['id']
    session.permanent = True
    return jsonify({'user': user}), 201

@app.route('/api/auth/login', methods=['POST'])
def auth_login():
    payload = request.get_json(silent=True) or {}
    email = auth_service.normalize_email(str(payload.get('email', '')))
    password = str(payload.get('password', ''))
    user = db.get_user_by_email(email)
    if not user or not user.get('password_hash') or not auth_service.password_matches(password, user['password_hash']):
        return jsonify({'error': 'Email or password is incorrect.'}), 401
    session.clear()
    session['user_id'] = user['id']
    session.permanent = True
    return jsonify({'user': public_user(user)})

@app.route('/api/auth/magic-link', methods=['POST'])
def auth_magic_link():
    payload = request.get_json(silent=True) or {}
    email = auth_service.normalize_email(str(payload.get('email', '')))
    if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', email):
        return jsonify({'error': 'Enter a valid email address.'}), 400
    user = db.get_user_by_email(email)
    response = {'message': 'If an account exists, a sign-in link is on its way.'}
    if not user:
        return jsonify(response)
    token = auth_service.issue_magic_token(user['id'])
    if not token:
        return jsonify({'error': 'Too many sign-in links requested. Try again in 15 minutes.'}), 429
    if app.testing or os.environ.get('AUTH_DEV_MODE') == '1':
        base_url = os.environ.get('APP_BASE_URL') or request.host_url.rstrip('/')
        response['dev_link'] = f'{base_url}/?magic={token}'
        return jsonify(response)
    base_url = os.environ.get('APP_BASE_URL') or request.host_url.rstrip('/')
    link = f'{base_url}/?magic={token}'
    try:
        if not auth_service.send_magic_email(email, link):
            return jsonify({'error': 'Email sign-in is not configured yet. Contact the site administrator.'}), 503
    except (OSError, smtplib.SMTPException):
        app.logger.exception('Magic-link email delivery failed')
        return jsonify({'error': 'We could not send the email right now. Please try again later.'}), 503
    return jsonify(response)

@app.route('/api/auth/verify', methods=['POST'])
def auth_verify_magic_link():
    payload = request.get_json(silent=True) or {}
    token = str(payload.get('token', ''))
    user = auth_service.consume_magic_token(token) if token else None
    if not user:
        return jsonify({'error': 'This sign-in link is invalid, expired, or already used.'}), 400
    session.clear()
    session['user_id'] = user['id']
    session.permanent = True
    return jsonify({'user': public_user(user)})

@app.route('/api/auth/logout', methods=['POST'])
def auth_logout():
    session.clear()
    return jsonify({'success': True})

@app.route('/api/moods', methods=['GET'])
def get_moods():
    """
    GET /api/moods -> returns list of all configured moods
    """
    return jsonify(omdb.all_moods())

@app.route('/api/recommend', methods=['GET'])
def get_recommendations():
    """
    GET /api/recommend?mood=X -> returns recommendations for mood X, along with the profile and excluded count.
    """
    mood = request.args.get('mood')
    supported_industries = {
        'hollywood', 'tollywood', 'ollywood', 'bollywood',
        'animation', 'korean', 'anime', 'japanese'
    }
    raw_industries = request.args.get('industries', '')
    requested_industries = {item.strip().lower() for item in raw_industries.split(',') if item.strip()}
    invalid_industries = requested_industries - supported_industries
    if invalid_industries:
        return jsonify({'error': f"Unsupported industry filter: {', '.join(sorted(invalid_industries))}"}), 400
    if not mood:
        return jsonify({"error": "Query parameter 'mood' is required"}), 400
        
    # Check case-insensitively
    profile = omdb.get_mood_profile(mood)
    if not profile:
        return jsonify({"error": f"Invalid mood: {mood}"}), 400

    # Log the mood session
    db.log_mood(mood, current_user_id())
    
    # Get watched imdb_ids to filter recommendations
    watched_ids = db.get_watched_ids(current_user_id())
    
    # Get recommendations and the count of movies excluded
    movies, excluded_count = omdb.get_mood_recommendations_with_excluded(
        mood,
        watched_ids,
        industries=requested_industries
    )
    
    # Retrieve all watched movies to score and rank candidates using NumPy logic
    watched_movies = db.get_watched_movies(current_user_id())
    ranked_movies = omdb.score_and_rank_recommendations(movies, mood, watched_movies)
    
    return jsonify({
        "movies": ranked_movies,
        "profile": profile,
        "excluded_count": excluded_count
    })

@app.route('/api/search', methods=['GET'])
def search_movies():
    """
    GET /api/search?q=X&page=N -> search movies and mark each with an is_watched boolean
    """
    query = request.args.get('q')
    if not query:
        return jsonify({"movies": [], "total_count": 0})
        
    page = request.args.get('page', default=1, type=int)
    
    movies, total_count = omdb.search_movies(query, page=page)
    
    # Mark if each movie is watched
    watched_ids = db.get_watched_ids(current_user_id())
    for m in movies:
        m['is_watched'] = m.get('imdb_id') in watched_ids
        
    return jsonify({
        "movies": movies,
        "total_count": total_count
    })

@app.route('/api/movie/<imdb_id>', methods=['GET'])
def get_movie_detail(imdb_id):
    """
    GET /api/movie/<imdb_id> -> get full detail, add is_watched field
    """
    detail = omdb.get_movie_detail(imdb_id=imdb_id)
    if not detail:
        return jsonify({"error": f"Movie not found with imdb_id: {imdb_id}"}), 404
        
    watched_ids = db.get_watched_ids(current_user_id())
    detail['is_watched'] = imdb_id in watched_ids
    return jsonify(detail)

@app.route('/api/watched', methods=['GET'])
def get_watched():
    """
    GET /api/watched -> list all watched movies
    """
    return jsonify(db.get_watched_movies(current_user_id()))

@app.route('/api/watched', methods=['POST'])
def add_watched():
    """
    POST /api/watched -> body: movie dict with imdbID (or imdb_id), call mark_watched
    """
    movie = request.json
    if not movie:
        return jsonify({"error": "Missing request body"}), 400
        
    # Map imdbID to imdb_id for database.py compatibility
    if 'imdbID' in movie and 'imdb_id' not in movie:
        movie['imdb_id'] = movie['imdbID']
        
    if not movie.get('imdb_id'):
        return jsonify({"error": "imdbID is required"}), 400
        
    try:
        db.mark_watched(movie, current_user_id())
        return jsonify({"success": True, "message": "Movie marked as watched"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/watched/<imdb_id>', methods=['DELETE'])
def delete_watched(imdb_id):
    """
    DELETE /api/watched/<imdb_id> -> delete from watched_movies table directly
    """
    conn = db.get_connection()
    try:
        with conn:
            conn.execute('DELETE FROM watched_movies WHERE imdb_id = ? AND user_id = ?', (imdb_id, current_user_id()))
        return jsonify({"success": True, "message": f"Movie {imdb_id} deleted from watched list"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        conn.close()

@app.route('/api/watchlist', methods=['GET'])
def get_watchlist():
    """
    GET /api/watchlist -> list watchlist
    """
    return jsonify(db.get_watchlist(current_user_id()))

@app.route('/api/watchlist', methods=['POST'])
def add_watchlist():
    """
    POST /api/watchlist -> body: movie dict, call add_to_watchlist
    """
    movie = request.json
    if not movie:
        return jsonify({"error": "Missing request body"}), 400
        
    # Map imdbID to imdb_id for database.py compatibility
    if 'imdbID' in movie and 'imdb_id' not in movie:
        movie['imdb_id'] = movie['imdbID']
        
    if not movie.get('imdb_id'):
        return jsonify({"error": "imdbID/imdb_id is required"}), 400
        
    success, message = db.add_to_watchlist(movie, current_user_id())
    status_code = 201 if success else 400
    return jsonify({
        "success": success,
        "message": message
    }), status_code

@app.route('/api/watchlist/<imdb_id>', methods=['DELETE'])
def delete_watchlist(imdb_id):
    """
    DELETE /api/watchlist/<imdb_id> -> call remove_from_watchlist
    """
    try:
        db.remove_from_watchlist(imdb_id, current_user_id())
        return jsonify({"success": True, "message": f"Movie {imdb_id} removed from watchlist"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """
    GET /api/stats -> return db.get_stats()
    """
    return jsonify(db.get_stats(current_user_id()))

@app.route('/api/analytics/data', methods=['GET'])
def get_analytics_data():
    """Return chart-ready watch and mood aggregates."""
    data = db.get_analytics_data(current_user_id())
    profiles = {item['mood']: item for item in omdb.all_moods()}
    for item in data['mood_counts']:
        profile = profiles.get(item['mood'], {})
        item['label'] = profile.get('label', item['mood'].capitalize())
        item['color'] = profile.get('color', '#548b79')
    return jsonify(data)

@app.route('/api/analytics/dashboard', methods=['GET'])
def get_analytics_dashboard():
    """
    Legacy global dashboards are disabled because WitchMovie analytics are private per account.
    """
    return jsonify({'error': 'Use the account-specific /api/analytics/data endpoint.'}), 410

@app.route('/api/analytics/refresh', methods=['POST'])
def refresh_analytics_dashboard():
    """
    Legacy global dashboards are disabled because WitchMovie analytics are private per account.
    """
    return jsonify({'error': 'Use the account-specific /api/analytics/data endpoint.'}), 410

@app.route('/')
@app.route('/index.html')
def serve_index():
    """
    Serve the production React build, falling back to the legacy entry page before a build.
    """
    dist_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dist')
    built_index = os.path.join(dist_path, 'index.html')
    if os.path.exists(built_index):
        return send_from_directory(dist_path, 'index.html')
    index_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'index.html')
    return send_file(index_path)

@app.route('/assets/<path:filename>')
def serve_react_assets(filename):
    dist_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dist')
    return send_from_directory(os.path.join(dist_path, 'assets'), filename)

@app.route('/witch-mark.svg')
def serve_witch_mark():
    dist_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dist')
    return send_from_directory(dist_path, 'witch-mark.svg')

if __name__ == '__main__':
    print("====================================================")
    print("Starting WitchMovie Flask API Server...")
    print("Connecting to SQLite database...")
    print("OMDB API Integration Ready.")
    print("Running local server on http://localhost:5000")
    print("====================================================")
    
    app.run(host='0.0.0.0', port=5000, debug=os.environ.get('FLASK_DEBUG') == '1')
