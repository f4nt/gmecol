from django.conf.urls.defaults import *

urlpatterns = patterns('gmecol.views.main',
    url('^$', 'index', name='index'),
    url('^game/(?P<remote_id>\d+)/$', 'game_detail', name='game-detail'),
    url('^game/(?P<game_id>\d+)/platform/(?P<platform_id>\d+)/$',
        'game_platform_detail', name='game-platform-detail'),
    url('^search/$', 'search', name='search'),
)

urlpatterns += patterns('gmecol.views.collection',
    url('^game/(?P<game_id>\d+)/platform/(?P<platform_id>\d+)/add/$',
        'add_game_to_collection', name='add-game-to-collection'),
    url('^collection/$', 'view_collection', name='view-collection'),
)
