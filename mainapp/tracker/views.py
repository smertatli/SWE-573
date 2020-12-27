from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth.models import User
from .models import Tracker
from django.views.decorators.csrf import csrf_exempt
import sys
from sqlalchemy import create_engine
from django.conf import settings
import pandas as pd
from . import tweet_collector 
#from background_task import background
#from background_task.models import Task
from django_q.tasks import async_task, schedule
from django_q.models import Schedule
from datetime import timedelta
from django.utils import timezone


def create_track(request):
    return render(request, 'tracker/create.html')

@csrf_exempt
def create_track_ajax(request):
    tracker_created = False
    task_created = False
    error = None
    if request.method == "POST":
        try:
            Tracker.objects.create(user=request.user,
                                query=request.POST.get('query'),
                                frequency_level1=request.POST.get('level1'),
                                frequency_level2=request.POST.get('level2'),
                                fetch_size = request.POST.get('fetch_size'),
                                max_tweet_id="0")
            tracker_created = True
            task_created = create_task()
        except:
            #print("-------------------", sys.exc_info()[0], request.user,request.POST.get('query'), request.POST.get('level1'),
            #request.POST.get('level2'),request.POST.get('fetch_size'))
            tracker_created = False
            task_created = False
            error = str(e)
    return JsonResponse({'tracker_created': tracker_created, 'task_created':task_created, 'error':error})


    
def dump():
    db_connection_url = "postgresql://{}:{}@{}:{}/{}".format(
    settings.DATABASES['default']['USER'],
    settings.DATABASES['default']['PASSWORD'],
    settings.DATABASES['default']['HOST'],
    settings.DATABASES['default']['PORT'],
    settings.DATABASES['default']['NAME'],
    )

    engine = create_engine(db_connection_url)


    
    df = pd.read_pickle('tracker/tweets.pckl').drop('index', axis=1)
    df.columns = ["tweet_id","text","author_id","created_at","lang","conversation_id","possibly_sensitive","in_reply_to_user_id","source","retweet_count","reply_count","like_count","quote_count","withheld","place_place_full_name","place_id","place_country","place_country_code","place_place_name","place_place_type","key"]
    df.to_sql('tweets_manual', engine, if_exists='append', index=False)

@csrf_exempt
def create_task():
    status = 'NOPE'
    try:
        schedule('tracker.tweet_collector.TweetCollector',
                
                schedule_type = 'I',
                minutes = 0.1,
                repeats = 5)
        status = True
    except:
        status = False
    return status
    

#@background
#def get_tweets():
#    tweet_collector.TweetCollector()
#    print('yes.....')
#
#Task.objects.all().delete()

