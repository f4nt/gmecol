from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save


class BaseModel(models.Model):
    ''' Abstract base model providing standard fields that most models in this
    project will require.
    '''

    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Platform(BaseModel):
    ''' Houses the various platforms that games are playable on, i.e. Xbox,
    PS3, etc.
    '''

    name = models.CharField(max_length=64)
    slug = models.SlugField(unique=True)
    image_url = models.TextField()
    remote_id = models.IntegerField()

    def __unicode__(self):
        return u'%s' % self.name


class Genre(BaseModel):
    ''' Genre the game belongs in '''

    name = models.CharField(max_length=64)
    slug = models.SlugField(unique=True)
    remote_id = models.IntegerField()

    def __unicode__(self):
        return u'%s' % self.name


class Game(BaseModel):
    ''' Table for holding game entries '''

    name = models.CharField(max_length=128)
    slug = models.SlugField(unique=True)
    platform = models.ForeignKey('Platform')
    image_url = models.TextField()
    remote_id = models.IntegerField()
    genres = models.ManyToManyField('Genre')

    def __unicode__(self):
        return u'%s' % self.name


class UserGame(BaseModel):
    ''' Through model for games owned by a user. Provides extra information
    for that M2M relationship such as game ratings.
    '''

    RATINGS = [(x, x) for x in range(0, 6)]

    game = models.ForeignKey('Game')
    user = models.ForeignKey('UserProfile')
    rating = models.IntegerField(choices=RATINGS, blank=True, null=True)
    for_trade = models.BooleanField(default=False)
    for_sale = models.BooleanField(default=False)

    def __unicode__(self):
        return u'%s - %s' % (self.game.platform, self.game.name)


class UserProfile(BaseModel):
    ''' Profile for tracking a user's information and catalog '''

    user = models.OneToOneField('auth.User')
    games = models.ManyToManyField('Game', through='UserGame')

    def __unicode__(self):
        return '%s' % self.user.username

    @property
    def platforms(self):
        return Platform.objects.filter(
            pk__in=self.games.all().values_list('platform', flat=True)
        )


class Message(BaseModel):
    ''' Model for holding private messages between users '''

    from_user = models.ForeignKey(User, related_name='from_user')
    to_user = models.ForeignKey(User, related_name='to_user')
    subject = models.CharField(max_length=256)
    body = models.TextField()
    read = models.BooleanField(default=False)
    deleted = models.BooleanField(default=False)

    def __unicode__(self):
        return u'From: %s, To: %s, Subject: %s' % (
            self.from_user.username,
            self.to_user.username,
            self.subject
        )

    class Meta:
        ordering = ('-created', )


def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

post_save.connect(create_user_profile, sender=User)
