/usr/src/mainapp/templates
# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models


class AccountsDeneme(models.Model):
    ad = models.CharField(max_length=100)

    class Meta:
        managed = False
        db_table = 'accounts_deneme'


class AccountsUser(models.Model):
    username = models.CharField(max_length=100)
    email = models.CharField(max_length=100)
    password = models.CharField(max_length=100)

    class Meta:
        managed = False
        db_table = 'accounts_user'


class AuthGroup(models.Model):
    name = models.CharField(unique=True, max_length=150)

    class Meta:
        managed = False
        db_table = 'auth_group'


class AuthGroupPermissions(models.Model):
    group = models.ForeignKey(AuthGroup, models.DO_NOTHING)
    permission = models.ForeignKey('AuthPermission', models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'auth_group_permissions'
        unique_together = (('group', 'permission'),)


class AuthPermission(models.Model):
    name = models.CharField(max_length=255)
    content_type = models.ForeignKey('DjangoContentType', models.DO_NOTHING)
    codename = models.CharField(max_length=100)

    class Meta:
        managed = False
        db_table = 'auth_permission'
        unique_together = (('content_type', 'codename'),)


class AuthUser(models.Model):
    password = models.CharField(max_length=128)
    last_login = models.DateTimeField(blank=True, null=True)
    is_superuser = models.BooleanField()
    username = models.CharField(unique=True, max_length=150)
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=150)
    email = models.CharField(max_length=254)
    is_staff = models.BooleanField()
    is_active = models.BooleanField()
    date_joined = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'auth_user'


class AuthUserGroups(models.Model):
    user = models.ForeignKey(AuthUser, models.DO_NOTHING)
    group = models.ForeignKey(AuthGroup, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'auth_user_groups'
        unique_together = (('user', 'group'),)


class AuthUserUserPermissions(models.Model):
    user = models.ForeignKey(AuthUser, models.DO_NOTHING)
    permission = models.ForeignKey(AuthPermission, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'auth_user_user_permissions'
        unique_together = (('user', 'permission'),)


class DjangoAdminLog(models.Model):
    action_time = models.DateTimeField()
    object_id = models.TextField(blank=True, null=True)
    object_repr = models.CharField(max_length=200)
    action_flag = models.SmallIntegerField()
    change_message = models.TextField()
    content_type = models.ForeignKey('DjangoContentType', models.DO_NOTHING, blank=True, null=True)
    user = models.ForeignKey(AuthUser, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'django_admin_log'


class DjangoContentType(models.Model):
    app_label = models.CharField(max_length=100)
    model = models.CharField(max_length=100)

    class Meta:
        managed = False
        db_table = 'django_content_type'
        unique_together = (('app_label', 'model'),)


class DjangoMigrations(models.Model):
    app = models.CharField(max_length=255)
    name = models.CharField(max_length=255)
    applied = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'django_migrations'


class DjangoSession(models.Model):
    session_key = models.CharField(primary_key=True, max_length=40)
    session_data = models.TextField()
    expire_date = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'django_session'


class TrackerCollectedtweets(models.Model):
    tweet_id = models.CharField(max_length=100)
    text = models.TextField()
    author_id = models.CharField(max_length=100)
    created_at = models.DateTimeField()
    lang = models.CharField(max_length=20)
    conversation_id = models.CharField(max_length=100, blank=True, null=True)
    possibly_sensitive = models.CharField(max_length=10, blank=True, null=True)
    in_reply_to_user_id = models.CharField(max_length=100, blank=True, null=True)
    source = models.CharField(max_length=100, blank=True, null=True)
    retweet_count = models.IntegerField(blank=True, null=True)
    reply_count = models.IntegerField(blank=True, null=True)
    like_count = models.IntegerField(blank=True, null=True)
    quote_count = models.IntegerField(blank=True, null=True)
    withheld = models.CharField(max_length=100, blank=True, null=True)
    place_place_full_name = models.CharField(max_length=100, blank=True, null=True)
    place_id = models.CharField(max_length=100, blank=True, null=True)
    place_country = models.CharField(max_length=100, blank=True, null=True)
    place_country_code = models.CharField(max_length=100, blank=True, null=True)
    place_place_name = models.CharField(max_length=100, blank=True, null=True)
    place_place_type = models.CharField(max_length=100, blank=True, null=True)
    key = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'tracker_collectedtweets'


class TrackerReferencedtweets(models.Model):
    tweet_id = models.CharField(max_length=100)
    text = models.TextField()
    author_id = models.CharField(max_length=100)
    created_at = models.DateTimeField()
    lang = models.CharField(max_length=20)
    conversation_id = models.CharField(max_length=100, blank=True, null=True)
    possibly_sensitive = models.CharField(max_length=10, blank=True, null=True)
    in_reply_to_user_id = models.CharField(max_length=100, blank=True, null=True)
    source = models.CharField(max_length=100, blank=True, null=True)
    retweet_count = models.IntegerField(blank=True, null=True)
    reply_count = models.IntegerField(blank=True, null=True)
    like_count = models.IntegerField(blank=True, null=True)
    quote_count = models.IntegerField(blank=True, null=True)
    withheld = models.CharField(max_length=100, blank=True, null=True)
    place_place_full_name = models.CharField(max_length=100, blank=True, null=True)
    place_id = models.CharField(max_length=100, blank=True, null=True)
    place_country = models.CharField(max_length=100, blank=True, null=True)
    place_country_code = models.CharField(max_length=100, blank=True, null=True)
    place_place_name = models.CharField(max_length=100, blank=True, null=True)
    place_place_type = models.CharField(max_length=100, blank=True, null=True)
    key = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'tracker_referencedtweets'


class TrackerTracker(models.Model):
    frequency_level1 = models.CharField(max_length=50, blank=True, null=True)
    frequency_level2 = models.CharField(max_length=50, blank=True, null=True)
    max_tweet_id = models.CharField(max_length=50, blank=True, null=True)
    query = models.CharField(max_length=512, blank=True, null=True)
    user = models.ForeignKey(AuthUser, models.DO_NOTHING, blank=True, null=True)
    fetch_size = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'tracker_tracker'


class TweetAnnotation(models.Model):
    tweet_id = models.CharField(max_length=100)
    domain_id = models.CharField(max_length=100)
    entity_id = models.CharField(max_length=100)
    key = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'tweet_annotation'


class TweetAnnotationDomain(models.Model):
    domain_id = models.CharField(max_length=100)
    domain_name = models.CharField(max_length=100)
    domain_desc = models.CharField(max_length=100)

    class Meta:
        managed = False
        db_table = 'tweet_annotation_domain'


class TweetAnnotationEntity(models.Model):
    entity_id = models.CharField(max_length=100)
    entity_name = models.CharField(max_length=100)
    entity_desc = models.CharField(max_length=100)

    class Meta:
        managed = False
        db_table = 'tweet_annotation_entity'


class TweetEntity(models.Model):
    tweet_id = models.CharField(max_length=100)
    category = models.CharField(max_length=100)
    start_pos = models.IntegerField(blank=True, null=True)
    end_pos = models.IntegerField(blank=True, null=True)
    probability = models.FloatField(blank=True, null=True)
    type_of = models.CharField(max_length=100)
    username = models.CharField(max_length=100)
    normalized_text = models.CharField(max_length=100)
    tag = models.CharField(max_length=100)
    url = models.CharField(max_length=100)
    expanded_url = models.CharField(max_length=100)
    display_url = models.CharField(max_length=100)
    url_title = models.CharField(max_length=100)
    url_description = models.CharField(max_length=100)
    key = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'tweet_entity'


class TweetMedia(models.Model):
    tweet_id = models.CharField(max_length=100)
    category = models.CharField(max_length=100)
    media_key = models.CharField(max_length=100)
    type = models.CharField(max_length=100)
    url = models.CharField(max_length=100)
    view_count = models.IntegerField(blank=True, null=True)
    duration_ms = models.IntegerField(blank=True, null=True)
    key = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'tweet_media'


class TweetUser(models.Model):
    user_id = models.CharField(max_length=100)
    username = models.CharField(max_length=100)
    created_at = models.DateTimeField()
    description = models.TextField()
    location = models.CharField(max_length=100)
    name = models.CharField(max_length=100)
    protected = models.CharField(max_length=100)
    url = models.CharField(max_length=100)
    verified = models.CharField(max_length=100)
    followers_count = models.IntegerField(blank=True, null=True)
    following_count = models.IntegerField(blank=True, null=True)
    tweet_count = models.IntegerField(blank=True, null=True)
    listed_count = models.IntegerField(blank=True, null=True)
    key = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'tweet_user'


class TweetsInfo(models.Model):
    tweet_id = models.CharField(max_length=100)
    text = models.TextField()
    author_id = models.CharField(max_length=100)
    created_at = models.DateTimeField()
    lang = models.CharField(max_length=20)
    conversation_id = models.CharField(max_length=100, blank=True, null=True)
    possibly_sensitive = models.CharField(max_length=10, blank=True, null=True)
    in_reply_to_user_id = models.CharField(max_length=100, blank=True, null=True)
    source = models.CharField(max_length=100, blank=True, null=True)
    retweet_count = models.IntegerField(blank=True, null=True)
    reply_count = models.IntegerField(blank=True, null=True)
    like_count = models.IntegerField(blank=True, null=True)
    quote_count = models.IntegerField(blank=True, null=True)
    withheld = models.CharField(max_length=100, blank=True, null=True)
    place_place_full_name = models.CharField(max_length=100, blank=True, null=True)
    place_id = models.CharField(max_length=100, blank=True, null=True)
    place_country = models.CharField(max_length=100, blank=True, null=True)
    place_country_code = models.CharField(max_length=100, blank=True, null=True)
    place_place_name = models.CharField(max_length=100, blank=True, null=True)
    place_place_type = models.CharField(max_length=100, blank=True, null=True)
    key = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'tweets_info'


class TweetsReferenced(models.Model):
    tweet_id = models.CharField(max_length=100)
    type = models.CharField(max_length=100)
    reference_tweet_id = models.CharField(max_length=100)
    key = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'tweets_referenced'


class TweetsReferencedInfo(models.Model):
    tweet_id = models.CharField(max_length=100)
    text = models.TextField()
    author_id = models.CharField(max_length=100)
    created_at = models.DateTimeField()
    lang = models.CharField(max_length=20)
    conversation_id = models.CharField(max_length=100, blank=True, null=True)
    possibly_sensitive = models.CharField(max_length=10, blank=True, null=True)
    in_reply_to_user_id = models.CharField(max_length=100, blank=True, null=True)
    source = models.CharField(max_length=100, blank=True, null=True)
    retweet_count = models.IntegerField(blank=True, null=True)
    reply_count = models.IntegerField(blank=True, null=True)
    like_count = models.IntegerField(blank=True, null=True)
    quote_count = models.IntegerField(blank=True, null=True)
    withheld = models.CharField(max_length=100, blank=True, null=True)
    key = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'tweets_referenced_info'
