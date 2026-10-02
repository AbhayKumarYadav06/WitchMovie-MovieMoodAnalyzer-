import os
import random
import requests
import numpy as np
from typing import Dict, List, Set, Tuple, Any, Optional

# OMDB base URL
OMDB_BASE_URL = "http://www.omdbapi.com/"

# API key variable (defaults to environment variable or your active key)
OMDB_API_KEY = os.environ.get("OMDB_API_KEY", "c03f5cda")

# Mood profiles configuration
MOOD_PROFILES: Dict[str, Dict[str, Any]] = {
    'happy': {
        'label': 'Happy',
        'emoji': '😊',
        'color': '#FAD02C',
        'genres': ['Comedy', 'Adventure', 'Family', 'Musical'],
        'searches': ['happy', 'joy', 'fun', 'laugh', 'smile'],
        'description': 'Lighthearted comedies and feel-good stories to boost your spirit.'
    },
    'sad': {
        'label': 'Sad',
        'emoji': '😢',
        'color': '#3A86C8',
        'genres': ['Drama', 'Romance'],
        'searches': ['sad', 'tear', 'cry', 'blue', 'lost'],
        'description': 'Emotional dramas and moving tales for a good cry and reflection.'
    },
    'excited': {
        'label': 'Excited',
        'emoji': '⚡',
        'color': '#FF6B6B',
        'genres': ['Action', 'Sci-Fi', 'Thriller'],
        'searches': ['fast', 'furious', 'kill', 'action', 'run'],
        'description': 'High-octane blockbusters, action-packed adventures, and wild rides.'
    },
    'scared': {
        'label': 'Scared',
        'emoji': '😱',
        'color': '#7F5A83',
        'genres': ['Horror', 'Mystery', 'Thriller'],
        'searches': ['dark', 'ghost', 'dead', 'fear', 'night'],
        'description': 'Spooky horror, psychological thrillers, and hair-raising suspense.'
    },
    'romantic': {
        'label': 'Romantic',
        'emoji': '💖',
        'color': '#FF7597',
        'genres': ['Romance', 'Comedy', 'Drama'],
        'searches': ['love', 'heart', 'date', 'kiss', 'romance'],
        'description': 'Heartwarming love stories, classic romances, and cute rom-coms.'
    },
    'bored': {
        'label': 'Bored',
        'emoji': '🥱',
        'color': '#8E9AAF',
        'genres': ['Fantasy', 'Sci-Fi', 'Mystery'],
        'searches': ['dream', 'wild', 'space', 'mystery', 'magic'],
        'description': 'Mind-bending puzzles, epic fantasy worlds, and gripping mysteries.'
    },
    'angry': {
        'label': 'Angry',
        'emoji': '😠',
        'color': '#D90429',
        'genres': ['Action', 'Crime', 'Thriller'],
        'searches': ['war', 'rage', 'fight', 'revenge', 'fury'],
        'description': 'Revenge thrillers, high-stakes combat, and stories of justice being served.'
    },
    'nostalgic': {
        'label': 'Nostalgic',
        'emoji': '🕰️',
        'color': '#E29578',
        'genres': ['Adventure', 'Biography', 'History', 'Family'],
        'searches': ['old', 'classic', 'gold', 'remember', 'time'],
        'description': 'Classic favorites, period dramas, and memories from days gone by.'
    }
}

def search_movies(query: str, page: int = 1) -> Tuple[List[Dict[str, Any]], int]:
    """
    Searches movies using OMDB API.
    Returns a tuple of (list of movie dicts, total_count).
    Each movie in list has keys: imdb_id, title, year, poster, type.
    """
    params = {
        'apikey': OMDB_API_KEY,
        's': query,
        'page': page,
        'type': 'movie'
    }
    try:
        response = requests.get(OMDB_BASE_URL, params=params, timeout=8)
        response.raise_for_status()
        data = response.json()
        
        if data.get('Response') == 'True':
            movies = []
            for item in data.get('Search', []):
                movies.append({
                    'imdb_id': item.get('imdbID'),
                    'title': item.get('Title'),
                    'year': item.get('Year'),
                    'poster': item.get('Poster'),
                    'type': item.get('Type')
                })
            
            try:
                total_count = int(data.get('totalResults', 0))
            except ValueError:
                total_count = len(movies)
                
            return movies, total_count
        return [], 0
    except Exception as e:
        print(f"OMDB API Error in search_movies: {e}")
        return [], 0

def get_movie_detail(imdb_id: Optional[str] = None, title: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Retrieves full movie details by imdbID or Title from OMDB API.
    Returns movie dict mapped to db columns or None if not found/error.
    """
    if not imdb_id and not title:
        return None
        
    params = {'apikey': OMDB_API_KEY}
    if imdb_id:
        params['i'] = imdb_id
    else:
        params['t'] = title
        
    try:
        response = requests.get(OMDB_BASE_URL, params=params, timeout=8)
        response.raise_for_status()
        data = response.json()
        
        if data.get('Response') == 'True':
            # Extract Rotten Tomatoes rating if present
            rt_rating = "N/A"
            for r in data.get('Ratings', []):
                if r.get('Source') == 'Rotten Tomatoes':
                    rt_rating = r.get('Value')
                    break
                    
            return {
                'imdb_id': data.get('imdbID'),
                'title': data.get('Title'),
                'year': data.get('Year'),
                'poster': data.get('Poster'),
                'genre': data.get('Genre'),
                'rating': data.get('imdbRating'),
                'plot': data.get('Plot'),
                'director': data.get('Director'),
                'cast': data.get('Actors'),
                'awards': data.get('Awards'),
                'runtime': data.get('Runtime'),
                'rated': data.get('Rated'),
                'metascore': data.get('Metascore'),
                'rotten_tomatoes': rt_rating,
                'country': data.get('Country'),
                'language': data.get('Language')
            }
        return None
    except Exception as e:
        print(f"OMDB API Error in get_movie_detail: {e}")
        return None

def get_mood_recommendations(
    mood: str,
    watched_ids_set: Set[str],
    count: int = 12,
    industries: Optional[Set[str]] = None
) -> List[Dict[str, Any]]:
    """
    Generates recommendations matching a mood:
    - shuffles mood's search terms
    - fetches movies for each term using search_movies
    - skips movies that are in watched_ids_set or already collected
    - fetches full details for each result
    - returns a list of movie dicts up to count
    """
    recs, _ = get_mood_recommendations_with_excluded(mood, watched_ids_set, count, industries)
    return recs

def matches_industry(movie: Dict[str, Any], industries: Set[str]) -> bool:
    """Match a detail record to one or more requested film industries."""
    if not industries:
        return True

    countries = {part.strip().casefold() for part in (movie.get('country') or '').split(',')}
    languages = {part.strip().casefold() for part in (movie.get('language') or '').split(',')}
    genres = {part.strip().casefold() for part in (movie.get('genre') or '').split(',')}
    matches = {
        'hollywood': bool(countries & {'usa', 'united states', 'united states of america'}),
        'tollywood': 'india' in countries and bool(languages & {'telugu'}),
        'ollywood': 'india' in countries and bool(languages & {'odia', 'oriya'}),
        'bollywood': 'india' in countries and bool(languages & {'hindi'}),
        'animation': 'animation' in genres,
        'korean': bool(countries & {'south korea', 'korea, republic of', 'republic of korea'}) or 'korean' in languages,
        'anime': 'animation' in genres and ('japan' in countries or 'japanese' in languages),
        'japanese': 'japan' in countries or 'japanese' in languages,
    }
    return any(matches.get(industry, False) for industry in industries)

def get_mood_recommendations_with_excluded(
    mood: str,
    watched_ids_set: Set[str],
    count: int = 12,
    industries: Optional[Set[str]] = None
) -> Tuple[List[Dict[str, Any]], int]:
    """
    Generates recommendations matching a mood and returns a tuple of
    (recommendations list, excluded_watched_count).
    """
    normalized_mood = mood.lower()
    if normalized_mood not in MOOD_PROFILES:
        print(f"Warning: Mood '{mood}' is not a valid mood key.")
        return [], 0
        
    profile = MOOD_PROFILES[normalized_mood]
    searches = list(profile['searches'])
    random.shuffle(searches)
    
    recommendations: List[Dict[str, Any]] = []
    seen_ids: Set[str] = set()
    excluded_count = 0
    
    for search_term in searches:
        if len(recommendations) >= count:
            break
            
        movies, _ = search_movies(search_term)
        for m in movies:
            imdb_id = m.get('imdb_id')
            if not imdb_id:
                continue
            if imdb_id in watched_ids_set:
                excluded_count += 1
                continue
            if imdb_id in seen_ids:
                continue
                
            # Fetch full details
            detail = get_movie_detail(imdb_id=imdb_id)
            if detail and matches_industry(detail, industries or set()):
                recommendations.append(detail)
                seen_ids.add(imdb_id)
                if len(recommendations) >= count:
                    break
            elif detail:
                seen_ids.add(imdb_id)
                    
    return recommendations[:count], excluded_count

def get_mood_profile(mood: str) -> Optional[Dict[str, Any]]:
    """
    Returns the profile dict for a given mood (case-insensitive).
    """
    return MOOD_PROFILES.get(mood.lower())

def all_moods() -> List[Dict[str, Any]]:
    """
    Returns list of mood dicts excluding searches/keywords keys.
    Each returned dict contains keys: mood, label, emoji, color, genres, description.
    """
    moods_list = []
    for key, val in MOOD_PROFILES.items():
        moods_list.append({
            'mood': key,
            'label': val.get('label'),
            'emoji': val.get('emoji'),
            'color': val.get('color'),
            'genres': val.get('genres'),
            'description': val.get('description')
        })
    return moods_list

def score_and_rank_recommendations(movies: List[Dict[str, Any]], mood: str, watched_movies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Scores each recommended movie using a NumPy array:
    - Weights by IMDb rating (40%)
    - Weights by release year (20%)
    - Weights by genre match frequency from past watched movies for that mood (40%)
    Returns the scored and sorted list of movies (highest score first).
    """
    if not movies:
        return []
        
    normalized_mood = mood.lower()
    if normalized_mood not in MOOD_PROFILES:
        return movies
        
    profile = MOOD_PROFILES[normalized_mood]
    target_genres = set(profile['genres'])
    
    # 1. Compute genre match frequency from watched movies associated with this mood's target genres
    watched_genre_counts: Dict[str, int] = {}
    for wm in watched_movies:
        genres_str = wm.get('genre')
        if not genres_str or genres_str == 'N/A':
            continue
        genres = [g.strip() for g in genres_str.split(',')]
        # If the watched movie overlaps with target genres for this mood, count its genres
        if any(g in target_genres for g in genres):
            for g in genres:
                watched_genre_counts[g] = watched_genre_counts.get(g, 0) + 1
                
    # 2. Extract metrics for candidates
    ratings = []
    years = []
    genre_matches = []
    
    for m in movies:
        # Rating
        r_val = 0.0
        try:
            r_str = m.get('rating')
            if r_str and r_str != 'N/A':
                r_val = float(r_str)
        except ValueError:
            pass
        ratings.append(r_val)
        
        # Year
        y_val = 2000
        try:
            y_str = m.get('year')
            if y_str and y_str != 'N/A':
                y_val = int(y_str[:4])
        except (ValueError, TypeError):
            pass
        years.append(y_val)
        
        # Genre match score
        g_score = 0
        g_str = m.get('genre')
        if g_str and g_str != 'N/A':
            genres = [g.strip() for g in g_str.split(',')]
            for g in genres:
                g_score += watched_genre_counts.get(g, 0)
        genre_matches.append(g_score)
        
    # Convert to NumPy arrays for vector calculations
    ratings_arr = np.array(ratings, dtype=float)
    years_arr = np.array(years, dtype=float)
    genre_arr = np.array(genre_matches, dtype=float)
    
    # Normalize ratings to [0, 1]
    norm_ratings = ratings_arr / 10.0
    
    # Normalize years to [0, 1] (clip between 1970 and 2026)
    norm_years = np.clip((years_arr - 1970) / (2026 - 1970), 0.0, 1.0)
    
    # Normalize genre match counts to [0, 1]
    max_genre_match = np.max(genre_arr) if len(genre_arr) > 0 else 0
    if max_genre_match > 0:
        norm_genres = genre_arr / max_genre_match
    else:
        norm_genres = np.zeros_like(genre_arr)
        
    # Calculate weighted score:
    # 40% rating, 20% release year, 40% genre match
    scores = 0.4 * norm_ratings + 0.2 * norm_years + 0.4 * norm_genres
    
    # Sort indices in descending order
    ranked_indices = np.argsort(scores)[::-1]
    
    ranked_movies = []
    for idx in ranked_indices:
        movie = movies[int(idx)].copy()
        movie['score'] = float(scores[int(idx)])
        ranked_movies.append(movie)
        
    return ranked_movies
