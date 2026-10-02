import os
import random
import requests
from typing import Dict, List, Set, Tuple, Any, Optional

# OMDB base URL
OMDB_BASE_URL = "http://www.omdbapi.com/"

# API key variable (defaults to environment variable or YOUR_KEY)
OMDB_API_KEY = os.environ.get("OMDB_API_KEY", "YOUR_KEY")

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
            return {
                'imdb_id': data.get('imdbID'),
                'title': data.get('Title'),
                'year': data.get('Year'),
                'poster': data.get('Poster'),
                'genre': data.get('Genre'),
                'rating': data.get('imdbRating'),
                'plot': data.get('Plot'),
            }
        return None
    except Exception as e:
        print(f"OMDB API Error in get_movie_detail: {e}")
        return None

def get_mood_recommendations(mood: str, watched_ids_set: Set[str], count: int = 12) -> List[Dict[str, Any]]:
    """
    Generates recommendations matching a mood:
    - shuffles mood's search terms
    - fetches movies for each term using search_movies
    - skips movies that are in watched_ids_set or already collected
    - fetches full details for each result
    - returns a list of movie dicts up to count
    """
    normalized_mood = mood.lower()
    if normalized_mood not in MOOD_PROFILES:
        print(f"Warning: Mood '{mood}' is not a valid mood key.")
        return []
        
    profile = MOOD_PROFILES[normalized_mood]
    searches = list(profile['searches'])
    random.shuffle(searches)
    
    recommendations: List[Dict[str, Any]] = []
    seen_ids: Set[str] = set()
    
    for search_term in searches:
        if len(recommendations) >= count:
            break
            
        movies, _ = search_movies(search_term)
        for m in movies:
            imdb_id = m.get('imdb_id')
            if not imdb_id:
                continue
            if imdb_id in watched_ids_set or imdb_id in seen_ids:
                continue
                
            # Fetch full details
            detail = get_movie_detail(imdb_id=imdb_id)
            if detail:
                recommendations.append(detail)
                seen_ids.add(imdb_id)
                if len(recommendations) >= count:
                    break
                    
    return recommendations[:count]

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
