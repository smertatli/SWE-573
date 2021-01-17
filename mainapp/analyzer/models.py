from django.db import models
from django.contrib.auth.models import User
 

class Processor_NLP(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=10000, null=True, blank=True)
    tracker = models.CharField(max_length=10000, null=True, blank=True)
    preproc = models.CharField(max_length=10000, null=True, blank=True)
    stopwords = models.TextField(null=True, blank=True)
    corrections = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.query
    
    