from django.db import models
from django.contrib.auth.models import User
from . import tweet_collector

class Tracker(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    query_name = models.CharField(max_length=100, null=True, blank=True)
    query = models.CharField(max_length=512, null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE,  null=True, blank=True)
    frequency_level1 = models.CharField(max_length=50, null=True, blank=True)
    frequency_level2 = models.IntegerField(null=True, blank=True)
    fetch_size = models.IntegerField(null=True, blank=True)
    date_start = models.DateField(null=True, blank=True)
    date_end = models.DateField(null=True, blank=True)

    def __str__(self):
        return self.query
    
