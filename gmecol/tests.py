from mock import Mock, patch

from django.test import TestCase
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User

from gmecol import models


class MockGBResponse(object):

    def __init__(self, id, image, name, platforms, genres):
        self.id = id
        self.image = image
        self.name = name
        self.platforms = platforms
        self.genres = genres


class TestMainGmeColViews(TestCase):

    def test_index(self):
        ''' Test the index view '''
        response = self.client.get(reverse('index'))
        self.assertEqual(response.status_code, 200)

    @patch('giantbomb.giantbomb.Api.search')
    def test_search_games(self, giant_mock):
        ''' Test the search for games view '''
        giant_mock.return_value = ''
        response = self.client.get(reverse('search'), {
            'name': 'mario'
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(giant_mock.call_args[0][0], 'mario')

    @patch('giantbomb.giantbomb.Api.getGame')
    def test_game_detail(self, giant_mock):
        genre_mock = Mock()
        genre_mock.id = 1
        genre_mock.name = 'test'
        game_mock = MockGBResponse(
            id=1,
            image=Mock(icon=''),
            name='Test',
            platforms=[Mock(id=1)],
            genres=[genre_mock, ]
        )
        giant_mock.return_value = game_mock
        response = self.client.get(reverse('game-detail', args=['1']))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['game_root'].remote_id, 1)
        self.assertEqual(response.context['games'].count(), 1)
        assert models.Genre.objects.filter(name='test').exists()

    @patch('giantbomb.giantbomb.Api.getGame')
    def test_game_detail_404(self, giant_mock):
        giant_mock.return_value = None
        response = self.client.get(reverse('game-detail', args=['1']))
        self.assertEqual(response.status_code, 404)

    def test_game_platform_detail(self):
        response = self.client.get(reverse('game-platform-detail',
            args=[8015, 122]
        ))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['game'].name, 'Quake')


class TestGmeColCollectionViews(TestCase):

    def setUp(self):
        super(TestGmeColCollectionViews, self).setUp()
        assert self.client.login(username='test_user', password='test')
        self.user = User.objects.get(username='test_user')
        self.quake = models.Game.objects.get(name='Quake')

    def _add_game_to_profile(self):
        ''' Helper function to add games to a user's profile for testing '''
        models.UserGame.objects.create(
            user=self.user.userprofile,
            game=self.quake
        )

    def test_add_game_to_collection(self):
        ''' Tests the addition of games to a user's collection. '''
        response = self.client.get(reverse('add-game-to-collection',
            args=[8015, 122]
        ))
        self.assertEqual(response.status_code, 302)
        assert self.quake in self.user.userprofile.games.all()

    def test_view_collection(self):
        ''' Test for viewing a user's collection '''
        response = self.client.get(reverse('add-game-to-collection',
            args=[8015, 122]
        ))
        response = self.client.get(reverse('view-collection'))
        self.assertEqual(response.status_code, 200)
        assert self.quake.platform in response.context['platforms']
        for genre in self.quake.genres.all():
            assert genre in response.context['genres']

    def test_view_collection_by_genre(self):
        ''' Test viewing collection of games grouped by genre '''
        self._add_game_to_profile()
        genre = self.quake.genres.all()[0]
        response = self.client.get(reverse('collection-by-genre',
            args=[genre.pk]
        ))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['genre'], genre)
        assert self.quake in response.context['games']

    def test_view_collection_by_platform(self):
        ''' Test viewing collection of games grouped by platform '''
        self._add_game_to_profile()
        response = self.client.get(reverse('collection-by-platform',
            args=[self.quake.platform.pk]
        ))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['platform'], self.quake.platform)
        assert self.quake in response.context['games']
