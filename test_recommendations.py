import unittest
from unittest.mock import patch, MagicMock
import recommendations

class TestOMDBRecommendationModule(unittest.TestCase):

    def test_get_mood_profile(self):
        # Test case-insensitivity
        happy_profile = recommendations.get_mood_profile("Happy")
        self.assertIsNotNone(happy_profile)
        self.assertEqual(happy_profile['label'], 'Happy')
        
        # Test non-existent mood
        fake_profile = recommendations.get_mood_profile("not-a-mood")
        self.assertIsNone(fake_profile)

    def test_all_moods(self):
        moods = recommendations.all_moods()
        self.assertEqual(len(moods), 8)
        
        # Assert keys
        first_mood = moods[0]
        self.assertIn('mood', first_mood)
        self.assertIn('label', first_mood)
        self.assertIn('emoji', first_mood)
        self.assertIn('color', first_mood)
        self.assertIn('genres', first_mood)
        self.assertIn('description', first_mood)
        
        # Assert "searches" is excluded
        self.assertNotIn('searches', first_mood)
        self.assertNotIn('keywords', first_mood)

    @patch('requests.get')
    def test_search_movies_success(self, mock_get):
        # Mock OMDB successful search response
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

        movies, count = recommendations.search_movies("happy")
        self.assertEqual(count, 1)
        self.assertEqual(len(movies), 1)
        self.assertEqual(movies[0]['imdb_id'], 'tt0116483')
        self.assertEqual(movies[0]['title'], 'Happy Gilmore')

    @patch('requests.get')
    def test_search_movies_failure(self, mock_get):
        # Mock OMDB API failure response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'Response': 'False',
            'Error': 'Movie not found!'
        }
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        movies, count = recommendations.search_movies("asdfghjkl")
        self.assertEqual(count, 0)
        self.assertEqual(len(movies), 0)

    @patch('requests.get')
    def test_get_movie_detail(self, mock_get):
        # Mock OMDB detailed response
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

        detail = recommendations.get_movie_detail(imdb_id='tt0116483')
        self.assertIsNotNone(detail)
        self.assertEqual(detail['title'], 'Happy Gilmore')
        self.assertEqual(detail['rating'], '7.0')
        self.assertEqual(detail['genre'], 'Comedy, Sport')

    @patch('requests.get')
    def test_get_mood_recommendations(self, mock_get):
        # Mock responses for search and detail APIs
        mock_response_search = MagicMock()
        mock_response_search.json.return_value = {
            'Response': 'True',
            'Search': [
                {'Title': 'Happy Movie 1', 'Year': '2020', 'imdbID': 'tt001', 'Type': 'movie', 'Poster': 'p1'},
                {'Title': 'Happy Movie 2', 'Year': '2021', 'imdbID': 'tt002', 'Type': 'movie', 'Poster': 'p2'},
            ],
            'totalResults': '2'
        }
        
        mock_response_detail1 = MagicMock()
        mock_response_detail1.json.return_value = {
            'Response': 'True',
            'Title': 'Happy Movie 1',
            'Year': '2020',
            'imdbID': 'tt001',
            'Poster': 'p1',
            'Genre': 'Comedy',
            'imdbRating': '8.0',
            'Plot': 'Fun story 1'
        }
        
        mock_response_detail2 = MagicMock()
        mock_response_detail2.json.return_value = {
            'Response': 'True',
            'Title': 'Happy Movie 2',
            'Year': '2021',
            'imdbID': 'tt002',
            'Poster': 'p2',
            'Genre': 'Comedy',
            'imdbRating': '7.5',
            'Plot': 'Fun story 2'
        }

        # We configure request.get side_effect to return search result then detail results
        def side_effect(url, params, timeout):
            response = MagicMock()
            response.status_code = 200
            if 's' in params:
                response.json.return_value = mock_response_search.json.return_value
            elif 'i' in params:
                if params['i'] == 'tt001':
                    response.json.return_value = mock_response_detail1.json.return_value
                elif params['i'] == 'tt002':
                    response.json.return_value = mock_response_detail2.json.return_value
            return response

        mock_get.side_effect = side_effect

        # Test where 'tt001' is already watched
        watched_ids = {'tt001'}
        recs = recommendations.get_mood_recommendations('happy', watched_ids, count=5)
        
        # 'tt001' should be skipped, returning only 'tt002'
        self.assertEqual(len(recs), 1)
        self.assertEqual(recs[0]['imdb_id'], 'tt002')
        self.assertEqual(recs[0]['title'], 'Happy Movie 2')

if __name__ == '__main__':
    unittest.main()
