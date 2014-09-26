from mock import Mock, patch

from django.test import TestCase
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from django.test.utils import override_settings

from friends import models as friends

from gmecol import models


class MockGBResponse(object):

    def __init__(self, id, image, name, platforms, genres):
        self.id = id
        self.name = name
        self.platforms = platforms
        self.genres = genres
        self.deck = 'Sample text'
        self.original_release_date = '2012-01-01 00:00:00'
        self.image = Mock(
            icon='icon',
            medium='med',
            small='sm',
            super='super',
            screen='screen',
            thumb='thumb',
            tiny='tiny'
        )


TEST_CACHES = CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
    }
}


@override_settings(CACHES=TEST_CACHES)
class BaseCase(TestCase):
    pass


class TestMainGmeColViews(BaseCase):

    fixtures = ['all_data.json']

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
        genre_mock = {'id': 1, 'name': 'test'}
        game_mock = MockGBResponse(
            id=1,
            image=Mock(icon=''),
            name='Test',
            platforms=[dict(id=1)],
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


class TestGmeColCollectionViews(BaseCase):

    fixtures = ['all_data.json']

    def setUp(self):
        super(TestGmeColCollectionViews, self).setUp()
        assert self.client.login(username='test_user', password='test')
        self.user = User.objects.get(username='test_user')
        self.quake = models.Game.objects.get(name='Quake')

    def _add_game_to_profile(self, wish=False):
        ''' Helper function to add games to a user's profile for testing '''
        models.UserGame.objects.create(
            user=self.user.userprofile,
            game=self.quake,
            wish=wish
        )

    def test_add_game_to_collection(self):
        ''' Tests the addition of games to a user's collection. '''
        response = self.client.get(reverse('add-game-to-collection',
            args=[self.quake.pk]
        ))
        self.assertEqual(response.status_code, 302)
        assert not self.user.userprofile.usergame_set.get(game=self.quake).wish

    def test_switch_from_wish_to_collection(self):
        ''' Tests that adding a game to your collection removes it from your
        wish list
        '''
        self._add_game_to_profile()
        response = self.client.get(reverse('add-game-to-collection',
            args=[self.quake.pk]
        ))
        self.assertEqual(response.status_code, 302)
        assert not self.user.userprofile.usergame_set.get(game=self.quake).wish

    def test_add_game_to_wishlist(self):
        ''' Test adding a game to a user's wishlist '''
        response = self.client.get(reverse('add-game-to-wish',
            args=[self.quake.pk]
        ))
        self.assertEqual(response.status_code, 302)
        assert self.user.userprofile.usergame_set.get(game=self.quake).wish

    def test_view_collection(self):
        ''' Test for viewing a user's collection '''
        self._add_game_to_profile()
        response = self.client.get(reverse('view-collection'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            self.user.userprofile.usergame_set.get(game=self.quake).pk,
            response.context['games'][0].pk
        )

    def test_view_wishlist(self):
        ''' Test for viewing a user's wishlist '''
        self._add_game_to_profile(True)
        response = self.client.get(reverse('wishlist'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            self.user.userprofile.usergame_set.get(game=self.quake, wish=True).pk,
            response.context['games'][0].pk
        )

    def test_view_game_in_collection(self):
        ''' Test viewing a game that's in your collection. Identical to
        wish list
        '''
        self._add_game_to_profile()
        response = self.client.get(reverse('game-platform-detail',
            args=[8015, 122]
        ))
        self.assertEqual(response.status_code, 200)
        assert response.context['user_game']

    def test_rate_game_in_collection_nonzero(self):
        ''' Tests rating functionality with positive number. Same for wish
        list
        '''
        self._add_game_to_profile()
        response = self.client.get(reverse('rate-game', args=[self.quake.pk]), {
            'score': '1',
        })
        self.assertEqual(response.status_code, 200)
        ug = models.UserGame.objects.get(
            user=self.user.userprofile,
            game__pk=self.quake.pk
        )
        self.assertEqual(ug.rating, 1)

    def test_rate_game_in_collection_reset(self):
        ''' Tests rating functionality with 0 to null the rating. Same for
        wish list
        '''
        self._add_game_to_profile()
        response = self.client.get(reverse('rate-game', args=[self.quake.pk]), {
            'score': '0',
        })
        self.assertEqual(response.status_code, 200)
        ug = models.UserGame.objects.get(
            user=self.user.userprofile,
            game__pk=self.quake.pk
        )
        self.assertEqual(ug.rating, None)

    def test_toggle_game_trade(self):
        ''' Tests the toggle abilities for for_trade on a game in a user's
        collection
        '''
        self._add_game_to_profile()
        # Toggle to True
        response = self.client.get(reverse('trade-game', args=[self.quake.pk]))
        self.assertEqual(response.status_code, 200)
        ug = models.UserGame.objects.get(
            user=self.user.userprofile,
            game__pk=self.quake.pk
        )
        self.assertTrue(ug.for_trade)

        # Toggle to False
        response = self.client.get(reverse('trade-game', args=[self.quake.pk]))
        ug = models.UserGame.objects.get(
            user=self.user.userprofile,
            game__pk=self.quake.pk
        )
        self.assertFalse(ug.for_trade)

    def test_toggle_game_sell(self):
        ''' Tests the toggle abilities for for_sale on a game in user's
        collection
        '''
        self._add_game_to_profile()
        # Toggle to True
        response = self.client.get(reverse('sell-game', args=[self.quake.pk]))
        self.assertEqual(response.status_code, 200)
        ug = models.UserGame.objects.get(
            user=self.user.userprofile,
            game__pk=self.quake.pk
        )
        self.assertTrue(ug.for_sale)

        # Toggle to False
        response = self.client.get(reverse('sell-game', args=[self.quake.pk]))
        ug = models.UserGame.objects.get(
            user=self.user.userprofile,
            game__pk=self.quake.pk
        )
        self.assertFalse(ug.for_sale)

    def test_view_collection_by_genre(self):
        ''' Test viewing collection of games grouped by genre '''
        self._add_game_to_profile()
        genre = self.quake.genres.all()[0]
        response = self.client.get(reverse('view-collection'), {
            'genre': genre.pk
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['genre'], genre)
        assert self.quake in [game.game for game in response.context['games']]
        assert not any([game.wish for game in response.context['games']])

    def test_view_wishlist_by_genre(self):
        ''' Test viewing wishlist of games grouped by genre '''
        self._add_game_to_profile(True)
        genre = self.quake.genres.all()[0]
        response = self.client.get(reverse('wishlist'), {
            'genre': genre.pk
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['genre'], genre)
        assert self.quake in [game.game for game in response.context['games']]
        assert all([game.wish for game in response.context['games']])

    def test_view_collection_by_platform(self):
        ''' Test viewing collection of games grouped by platform '''
        self._add_game_to_profile()
        response = self.client.get(reverse('view-collection'), {
            'platform': self.quake.platform.pk
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['platform'], self.quake.platform)
        assert self.quake in [game.game for game in response.context['games']]
        assert not any([game.wish for game in response.context['games']])

    def test_view_wishlist_by_platform(self):
        ''' Test viewing wishlist of games grouped by platform '''
        self._add_game_to_profile(True)
        response = self.client.get(reverse('wishlist'), {
            'platform': self.quake.platform.pk
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['platform'], self.quake.platform)
        assert self.quake in [game.game for game in response.context['games']]
        assert all([game.wish for game in response.context['games']])


class TestGmeColProfileViews(BaseCase):

    fixtures = ['all_data.json']

    def setUp(self):
        super(TestGmeColProfileViews, self).setUp()
        assert self.client.login(username='test_user', password='test')
        self.user = User.objects.get(username='test_user')
        friends.Friendship.objects.create(user=self.user)

    def test_view_own_profile(self):
        ''' Test viewing the user's profile '''
        response = self.client.get(reverse('profile', args=[self.user.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['user'], self.user)

    def test_view_other_profile(self):
        ''' Test viewing someone else's profile '''
        user = User.objects.create(username='other_test')
        response = self.client.get(reverse('profile', args=[user.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['user'], user)


class TestGmeColMessagingViews(BaseCase):

    fixtures = ['all_data.json']
    ''' Test messaging functionality '''

    def setUp(self):
        super(TestGmeColMessagingViews, self).setUp()
        assert self.client.login(username='test_user', password='test')
        self.user = User.objects.get(username='test_user')
        friends.Friendship.objects.create(user=self.user)

        self.friend = User.objects.create(username='friend')
        self.friend.friendship.friends.add(self.user.friendship)

    def _create_message(self, from_user, to_user, subject, body):
        ''' helper function to create messages '''
        return models.Message.objects.create(
            from_user=from_user,
            to_user=to_user,
            subject=subject,
            body=body
        )

    def test_send_message_to_friend(self):
        ''' Test sending a message to a friend '''
        response = self.client.post(reverse('send-message'), {
            'from_user': self.user.pk,
            'to_user': self.friend.pk,
            'subject': 'test',
            'body': 'test',
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            models.Message.objects.filter(
                subject='test',
                body='test',
                from_user=self.user,
                to_user=self.friend
            ).exists()
        )

    def test_view_message_list(self):
        ''' Test viewing a user's messages. Shows we don't show sent
        or deleted messages
        '''
        self._create_message(self.friend, self.user, 'Test1', 'Testing')
        self._create_message(self.friend, self.user, 'Test2', 'Testing')
        self._create_message(self.user, self.friend, 'Test2', 'Testing')
        message = self._create_message(
            self.friend, self.user, 'Test2', 'Testing')
        message.deleted = True
        message.save()
        response = self.client.get(reverse('message-list'))
        self.assertEqual(response.context['messages'].count(), 2)

    def test_view_message_list_sent(self):
        ''' Test proving that we only show sent messages with the sent
        filtering on message-list
        '''
        self._create_message(self.friend, self.user, 'Test1', 'Testing')
        self._create_message(self.friend, self.user, 'Test2', 'Testing')
        self._create_message(self.user, self.friend, 'Test2', 'Testing')
        message = self._create_message(
            self.friend, self.user, 'Test2', 'Testing')
        message.deleted = True
        message.save()
        response = self.client.get(reverse('message-list'), {
            'folder': 'sent'
        })
        self.assertEqual(response.context['messages'].count(), 1)

    def test_view_message_list_deleted(self):
        ''' Test proving that we only show deleted messages with the deleted
        filtering on message-list
        '''
        self._create_message(self.friend, self.user, 'Test1', 'Testing')
        self._create_message(self.friend, self.user, 'Test2', 'Testing')
        self._create_message(self.user, self.friend, 'Test2', 'Testing')
        self._create_message(self.user, self.friend, 'Test2', 'Testing')
        message = self._create_message(
            self.friend, self.user, 'Test2', 'Testing')
        message.deleted = True
        message.save()
        response = self.client.get(reverse('message-list'), {
            'folder': 'deleted'
        })
        self.assertEqual(response.context['messages'].count(), 1)


class TestGmeColFriendViews(BaseCase):

    fixtures = ['all_data.json']

    def setUp(self):
        super(TestGmeColFriendViews, self).setUp()
        assert self.client.login(username='test_user', password='test')
        self.user = User.objects.get(username='test_user')
        friends.Friendship.objects.create(user=self.user)

        self.friend = User.objects.create(username='friend_test')
        self.friend.friendship.friends.add(self.user.friendship)

    def test_list_friends(self):
        ''' Tests the friends list view '''
        response = self.client.get(reverse('list-friends'))
        self.assertContains(response, 'friend_test')

    def test_add_friend(self):
        ''' Tests creating a friendship request '''
        new_friend = User.objects.create(username='add_friend_test')
        response = self.client.post(
            reverse('add-friend', args=[new_friend.pk]),
            {
                'to_user': new_friend.pk,
                'from_user': self.user.pk,
                'subject': 'Friendship Request',
                'body': 'Be my friend!'
            }
        )
        self.assertEqual(response.status_code, 302)
        assert models.Message.objects.filter(
            from_user=self.user,
            to_user=new_friend,
            subject='Friendship Request',
            body='Be my friend!'
        ).exists()
        assert friends.FriendshipRequest.objects.filter(
            from_user=self.user,
            to_user=new_friend,
            accepted=False
        )

    def test_remove_friend(self):
        ''' Tests that we can kill a friendship '''
        response = self.client.get(
            reverse('remove-friend', args=[self.friend.pk])
        )
        self.assertEqual(response.status_code, 302)
        assert not self.user.friendship.friends.all()
