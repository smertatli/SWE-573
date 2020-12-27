from django.db import models
from django.contrib.auth.models import User
from . import tweet_collector

class Tracker(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    query = models.CharField(max_length=512, null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE,  null=True, blank=True)
    frequency_level1 = models.CharField(max_length=50, null=True, blank=True)
    frequency_level2 = models.CharField(max_length=50, null=True, blank=True)
    fetch_size = models.IntegerField(null=True, blank=True)
    max_tweet_id = models.CharField(max_length=50, null=True, blank=True)

    def __str__(self):
        return self.query
    

class TweetAnnotation(models.Model):
    tweet_id = models.CharField(max_length=100)
    domain_id = models.CharField(max_length=100, blank=True, null=True)
    entity_id = models.CharField(max_length=100, blank=True, null=True)
    key = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'tweet_annotation'


class TweetAnnotationDomain(models.Model):
    domain_id = models.CharField(max_length=100)
    domain_name = models.CharField(max_length=100, blank=True, null=True)
    domain_desc = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'tweet_annotation_domain'


class TweetAnnotationEntity(models.Model):
    entity_id = models.CharField(max_length=100)
    entity_name = models.CharField(max_length=100, blank=True, null=True)
    entity_desc = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'tweet_annotation_entity'


class TweetEntity(models.Model):
    tweet_id = models.CharField(max_length=100)
    category = models.CharField(max_length=100, blank=True, null=True)
    start_pos = models.IntegerField(blank=True, null=True)
    end_pos = models.IntegerField(blank=True, null=True)
    probability = models.FloatField(blank=True, null=True)
    type_of = models.CharField(max_length=100, blank=True, null=True)
    username = models.CharField(max_length=100, blank=True, null=True)
    normalized_text = models.CharField(max_length=100, blank=True, null=True)
    tag = models.CharField(max_length=100, blank=True, null=True)
    url = models.CharField(max_length=100, blank=True, null=True)
    expanded_url = models.CharField(max_length=100, blank=True, null=True)
    display_url = models.CharField(max_length=100, blank=True, null=True)
    url_title = models.CharField(max_length=100, blank=True, null=True)
    url_description = models.CharField(max_length=100, blank=True, null=True)
    key = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'tweet_entity'


class TweetInfo(models.Model):
    tweet_id = models.CharField(max_length=100)
    text = models.TextField()
    author_id = models.CharField(max_length=100)
    created_at = models.DateTimeField()
    lang = models.CharField(max_length=20, blank=True, null=True)
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
        db_table = 'tweet_info'


class TweetMedia(models.Model):
    tweet_id = models.CharField(max_length=100)
    category = models.CharField(max_length=100)
    media_key = models.CharField(max_length=100)
    type = models.CharField(max_length=100, blank=True, null=True)
    url = models.CharField(max_length=100, blank=True, null=True)
    view_count = models.IntegerField(blank=True, null=True)
    duration_ms = models.IntegerField(blank=True, null=True)
    key = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'tweet_media'


class TweetReferenced(models.Model):
    tweet_id = models.CharField(max_length=100)
    type = models.CharField(max_length=100)
    reference_tweet_id = models.CharField(max_length=100)
    key = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'tweet_referenced'


class TweetReferencedInfo(models.Model):
    tweet_id = models.CharField(max_length=100)
    text = models.TextField()
    author_id = models.CharField(max_length=100)
    created_at = models.DateTimeField()
    lang = models.CharField(max_length=20, blank=True, null=True)
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
        db_table = 'tweet_referenced_info'


class TweetUser(models.Model):
    user_id = models.CharField(max_length=100)
    username = models.CharField(max_length=100)
    created_at = models.DateTimeField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    location = models.CharField(max_length=100, blank=True, null=True)
    name = models.CharField(max_length=100, blank=True, null=True)
    protected = models.CharField(max_length=100, blank=True, null=True)
    url = models.CharField(max_length=100, blank=True, null=True)
    verified = models.CharField(max_length=100, blank=True, null=True)
    followers_count = models.IntegerField(blank=True, null=True)
    following_count = models.IntegerField(blank=True, null=True)
    tweet_count = models.IntegerField(blank=True, null=True)
    listed_count = models.IntegerField(blank=True, null=True)
    key = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'tweet_user'


#tweet_collector.TweetCollector()