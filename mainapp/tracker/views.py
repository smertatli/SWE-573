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
from datetime import datetime

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
            name=request.POST.get('name')
            query=request.POST.get('query')
            frequency_level1=request.POST.get('level1')
            frequency_level2=request.POST.get('level2')
            fetch_size = request.POST.get('fetch_size')
            date_start = request.POST.get('date_start')
            date_end = request.POST.get('date_end')

            Tracker.objects.create(user=user,
                                    query_name = name,
                                    query=query,
                                    frequency_level1=frequency_level1,
                                    frequency_level2=frequency_level2,
                                    fetch_size = fetch_size,
                                    date_start = date_start,
                                    date_end = date_end 
                                    )
            tracker_created = True
            task_created = create_task(name, query, frequency_level1, frequency_level2, fetch_size, date_start, date_end, manual=False)
        except:
            tracker_created = False
            task_created = False
            error = str(e)
    return JsonResponse({'tracker_created': tracker_created, 'task_created':task_created, 'error':error})


    

@csrf_exempt
def create_task(name, query, frequency_level1, frequency_level2, fetch_size, date_start, date_end, manual=True):
    status = 'NOPE'

    date_start = datetime.strptime(date_start, "%Y-%m-%d")
    date_end =  datetime.strptime(date_end, "%Y-%m-%d")

    day_diff = (date_end - date_start).days

    if frequency_level1 == 'minute':
        schedule_type = 'I'
        repeat = day_diff * 24 * 60
    else:
        schedule_type ='H'
        repeat = day_diff * 24
      

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
                    query_name=name,
                    manual = manual,
                    schedule_type = schedule_type,
                    
                    minutes = 1,
                    repeats = repeat
                    )
            status = True
        except:
            status = False
    return status
    

def display_my_tracks(request):
    return HttpResponse('OLDUĞ')