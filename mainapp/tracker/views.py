from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.models import User
from .models import Tracker
from django.views.decorators.csrf import csrf_exempt
import sys
from sqlalchemy import create_engine
from django.conf import settings
import pandas as pd
from . import tweet_collector 
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
            user=request.user
            query=request.POST.get('query')
            frequency_level1=request.POST.get('level1')
            frequency_level2=request.POST.get('level2')
            fetch_size = request.POST.get('fetch_size')
            Tracker.objects.create(user=user,
                                    query=query,
                                    frequency_level1=frequency_level1,
                                    frequency_level2=frequency_level2,
                                    fetch_size = fetch_size,
                                    max_tweet_id="0")
            tracker_created = True
            task_created = create_task(query, frequency_level1, frequency_level2, fetch_size)
        except:
            tracker_created = False
            task_created = False
            error = str(e)
    return JsonResponse({'tracker_created': tracker_created, 'task_created':task_created, 'error':error})


    

@csrf_exempt
def create_task(query, frequency_level1, frequency_level2, fetch_size, manual=True):
    status = 'NOPE'
    if manual:
        try:
            tweet_collector.TweetCollector(None, None, manual = manual)
            status = True
        except Exception as e:
            print('########################### False', str(e))
            status = False
    else:
        try:
            schedule('tracker.tweet_collector.TweetCollector',
                    query = query,
                    fetch_size = fetch_size,
                    schedule_type = 'I',
                    minutes = 1,
                    repeats = 10)
            status = True
        except:
            status = False
    return status
    

def display_my_tracks(request):
    return HttpResponse('OLDUĞ')