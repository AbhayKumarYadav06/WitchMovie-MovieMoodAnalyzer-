import unittest
from unittest.mock import patch, MagicMock
import omdb

class TestOMDBModule(unittest.TestCase):

    def test_get_mood_profile(self):
        happy_profile = omdb.get_mood_profile("Happy")
        self.assertIsNotNone(happy_profile)
        self.assertEqual(happy_profile['label'], 'Happy')
        
        fake_profile = omdb.get_mood_profile("not-a-mood")
        self.assertIsNone(fake_profile)

    def test_all_moods(self):
        moods = omdb.all_moods()
        self.assertEqual(len(moods), 8)
        
        first_mood = moods[0]
        self.assertIn('mood', first_mood)
        self.assertIn('label', first_mood)
        self.assertIn('emoji', first_mood)
        self.assertIn('color', first_mood)
        self.assertIn('genres', first_mood)
        self.assertIn('description', first_mood)
        
        self.assertNotIn('searches', first_mood)

    @patch('requests.get')
    def test_search_movies_success(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'Response': 'True',
            'Search': [
                {'Title': 'Happy Gilmore', 'Year': '1996', 'imdbID': 'tt0116483', 'Type': 'movie', 'Poster': 'poster_url'}
            ],
            'totalResults': '1'
        }
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        movies, count = omdb.search_movies("happy")
        self.assertEqual(count, 1)
        self.assertEqual(len(movies), 1)
        self.assertEqual(movies[0]['imdb_id'], 'tt0116483')
        self.assertEqual(movies[0]['title'], 'Happy Gilmore')

    @patch('requests.get')
    def test_get_movie_detail(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'Response': 'True',
            'Title': 'Happy Gilmore',
            'Year': '1996',
            'imdbID': 'tt0116483',
            'Poster': 'poster_url',
            'Genre': 'Comedy, Sport',
            'imdbRating': '7.0',
            'Plot': 'A rejected hockey player puts his skills to the golf course.'
        }
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        detail = omdb.get_movie_detail(imdb_id='tt0116483')
        self.assertIsNotNone(detail)
        self.assertEqual(detail['title'], 'Happy Gilmore')
        self.assertEqual(detail['rating'], '7.0')

    def test_score_and_rank_recommendations(self):
        # Movie candidates
        candidates = [
            {'imdb_id': 'tt001', 'title': 'High Rating Old Comedy', 'rating': '9.5', 'year': '1980', 'genre': 'Comedy'},
            {'imdb_id': 'tt002', 'title': 'Low Rating New Comedy', 'rating': '5.0', 'year': '2020', 'genre': 'Comedy'},
            {'imdb_id': 'tt003', 'title': 'Mid Rating New Drama', 'rating': '7.5', 'year': '2022', 'genre': 'Drama'}
        ]
        
        # Watched history (Comedy matches 'happy' profile target genres)
        watched_history = [
            {'imdb_id': 'tt101', 'genre': 'Comedy'},
            {'imdb_id': 'tt102', 'genre': 'Comedy'},
            {'imdb_id': 'tt103', 'genre': 'Sci-Fi'} # Doesn't overlap with 'happy' target genres (Comedy, Adventure, Family, Musical)
        ]
        
        ranked = omdb.score_and_rank_recommendations(candidates, 'happy', watched_history)
        
        self.assertEqual(len(ranked), 3)
        
        # 'score' field should be attached to each movie dict
        self.assertIn('score', ranked[0])
        self.assertIn('score', ranked[1])
        self.assertIn('score', ranked[2])
        
        # High Rating Old Comedy should rank first (40% * 9.5/10 + 40% * 1.0 (genre match) is very high)
        self.assertEqual(ranked[0]['imdb_id'], 'tt001')
        
        # Scores should be in descending order
        self.assertGreaterEqual(ranked[0]['score'], ranked[1]['score'])
        self.assertGreaterEqual(ranked[1]['score'], ranked[2]['score'])

    def test_matches_industry_filters(self):
        self.assertTrue(omdb.matches_industry(
            {'country': 'India', 'language': 'Telugu', 'genre': 'Drama'},
            {'tollywood'}
        ))
        self.assertTrue(omdb.matches_industry(
            {'country': 'India', 'language': 'Oriya, Odia', 'genre': 'Drama'},
            {'ollywood'}
        ))
        self.assertTrue(omdb.matches_industry(
            {'country': 'Japan', 'language': 'Japanese', 'genre': 'Animation, Adventure'},
            {'anime'}
        ))
        self.assertFalse(omdb.matches_industry(
            {'country': 'India', 'language': 'Hindi', 'genre': 'Drama'},
            {'tollywood'}
        ))
        self.assertTrue(omdb.matches_industry({'country': 'India'}, set()))

    @patch('omdb.get_movie_detail')
    @patch('omdb.search_movies')
    def test_mood_recommendations_skip_non_matching_industries(self, mock_search, mock_detail):
        mock_search.return_value = ([
            {'imdb_id': 'tt-us'},
            {'imdb_id': 'tt-telugu'}
        ], 2)
        mock_detail.side_effect = [
            {'imdb_id': 'tt-us', 'title': 'US film', 'country': 'United States', 'language': 'English'},
            {'imdb_id': 'tt-telugu', 'title': 'Telugu film', 'country': 'India', 'language': 'Telugu'}
        ]

        movies, excluded = omdb.get_mood_recommendations_with_excluded(
            'happy', set(), count=1, industries={'tollywood'}
        )

        self.assertEqual(excluded, 0)
        self.assertEqual([movie['imdb_id'] for movie in movies], ['tt-telugu'])
        self.assertEqual(mock_detail.call_count, 2)

if __name__ == '__main__':
    unittest.main()
