import os
import unittest
import database

# Override database file to use a separate test database
database.DB_PATH = os.path.join(os.path.dirname(os.path.abspath(database.__file__)), 'test_movies.db')
DB_FILE = database.DB_PATH

class TestMovieMoodAnalyzerDatabase(unittest.TestCase):
    
    def setUp(self):
        # Ensure database is removed before each test
        if os.path.exists(DB_FILE):
            try:
                os.remove(DB_FILE)
            except OSError:
                pass
        database.init_db()

    def tearDown(self):
        # Clean up database after each test
        if os.path.exists(DB_FILE):
            try:
                os.remove(DB_FILE)
            except OSError:
                pass

    def test_init_db_creates_tables(self):
        # Tables should be successfully created and queried without error
        conn = database.get_connection()
        try:
            # Query sqlite_master to verify tables exist
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = {row['name'] for row in cursor.fetchall()}
            self.assertIn('watched_movies', tables)
            self.assertIn('watchlist', tables)
            self.assertIn('mood_sessions', tables)
        finally:
            conn.close()

    def test_add_to_watchlist_and_get(self):
        movie = {
            'imdb_id': 'tt0111161',
            'title': 'The Shawshank Redemption',
            'year': '1994',
            'poster': 'https://example.com/shawshank.jpg',
            'genre': 'Drama',
            'rating': '9.3',
            'plot': 'Over the course of several years, two convicts form a friendship...',
        }
        
        # Add movie
        success, msg = database.add_to_watchlist(movie)
        self.assertTrue(success)
        self.assertIn("success", msg.lower())
        
        # Try adding the same movie again
        success2, msg2 = database.add_to_watchlist(movie)
        self.assertFalse(success2)
        self.assertIn("already in the watchlist", msg2.lower())
        
        # Get watchlist
        watchlist = database.get_watchlist()
        self.assertEqual(len(watchlist), 1)
        self.assertEqual(watchlist[0]['imdb_id'], 'tt0111161')
        self.assertEqual(watchlist[0]['title'], 'The Shawshank Redemption')
        
    def test_remove_from_watchlist(self):
        movie = {
            'imdb_id': 'tt0111161',
            'title': 'The Shawshank Redemption',
        }
        database.add_to_watchlist(movie)
        self.assertEqual(len(database.get_watchlist()), 1)
        
        database.remove_from_watchlist('tt0111161')
        self.assertEqual(len(database.get_watchlist()), 0)

    def test_mark_watched(self):
        movie = {
            'imdb_id': 'tt0087538',
            'title': 'The Karate Kid',
            'year': '1984',
            'poster': 'https://example.com/karate_kid.jpg',
            'genre': 'Action, Drama, Family',
            'rating': '7.3',
            'plot': 'A martial arts master agrees to teach karate to a bullied teen.',
        }
        
        # Add to watchlist first
        database.add_to_watchlist(movie)
        self.assertEqual(len(database.get_watchlist()), 1)
        self.assertEqual(len(database.get_watched_movies()), 0)
        self.assertEqual(database.get_watched_ids(), set())
        
        # Mark as watched
        database.mark_watched(movie)
        
        # Should be removed from watchlist and added to watched_movies
        self.assertEqual(len(database.get_watchlist()), 0)
        watched_movies = database.get_watched_movies()
        self.assertEqual(len(watched_movies), 1)
        self.assertEqual(watched_movies[0]['imdb_id'], 'tt0087538')
        self.assertEqual(watched_movies[0]['title'], 'The Karate Kid')
        self.assertEqual(database.get_watched_ids(), {'tt0087538'})

        # Mark watched again (should update/overwrite instead of crash)
        movie_updated = movie.copy()
        movie_updated['title'] = 'The Karate Kid (Special Edition)'
        database.mark_watched(movie_updated)
        
        watched_movies = database.get_watched_movies()
        self.assertEqual(len(watched_movies), 1)
        self.assertEqual(watched_movies[0]['title'], 'The Karate Kid (Special Edition)')
        
        # Test add to watchlist skips if already watched
        success, msg = database.add_to_watchlist(movie)
        self.assertFalse(success)
        self.assertIn("already been watched", msg.lower())

    def test_log_mood_and_stats(self):
        # Check initial stats
        stats = database.get_stats()
        self.assertEqual(stats['watched_count'], 0)
        self.assertEqual(stats['watchlist_count'], 0)
        self.assertIsNone(stats['top_mood'])
        
        # Add movies
        database.add_to_watchlist({'imdb_id': 'tt1', 'title': 'Movie 1'})
        database.add_to_watchlist({'imdb_id': 'tt2', 'title': 'Movie 2'})
        database.mark_watched({'imdb_id': 'tt3', 'title': 'Movie 3'})
        
        # Log some moods
        database.log_mood("Happy")
        database.log_mood("Excited")
        database.log_mood("Happy")
        
        # Check updated stats
        stats = database.get_stats()
        self.assertEqual(stats['watched_count'], 1)
        self.assertEqual(stats['watchlist_count'], 2)
        self.assertEqual(stats['top_mood'], "Happy")

    def test_movie_history_is_isolated_per_account(self):
        first = database.create_account('first@example.com', 'First', None)
        second = database.create_account('second@example.com', 'Second', None)
        movie = {'imdb_id': 'tt-shared', 'title': 'Shared film'}

        self.assertTrue(database.add_to_watchlist(movie, first['id'])[0])
        self.assertTrue(database.add_to_watchlist(movie, second['id'])[0])
        self.assertEqual(len(database.get_watchlist(first['id'])), 1)
        self.assertEqual(len(database.get_watchlist(second['id'])), 1)
        self.assertEqual(database.get_watchlist(), [])

if __name__ == '__main__':
    unittest.main()
