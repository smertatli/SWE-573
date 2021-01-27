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
from sqlalchemy import create_engine
from django.contrib.auth.decorators import login_required

db_connection_url = "postgresql://{}:{}@{}:{}/{}".format(
settings.DATABASES['default']['USER'],
settings.DATABASES['default']['PASSWORD'],
settings.DATABASES['default']['HOST'],
settings.DATABASES['default']['PORT'],
settings.DATABASES['default']['NAME'],
)




@login_required
def create_track(request):
    
    if request.method == 'POST':
        trackers = request.POST.get('dummy')
        engine = create_engine(db_connection_url)
        temp_all = pd.read_sql_query("""
            select a.id, b.id as schedule_id, u.username, concat(query_name,'(id=',a.id::varchar(255),')') as query_name, query, frequency_level1, frequency_level2, fetch_size,
            date_start, date_end, coalesce(repeats,0) as repeat
            from tracker_tracker a
            inner join auth_user u on a.user_id = u.id and a.id in ({0}) 
            left join django_q_schedule b on position(concat('''',a.query_name,'''') in b.kwargs) > 0  
            and b.func = 'tracker.tweet_collector.TweetCollector' 
            """.format(trackers), engine)
        print(temp_all, trackers)

        successes = ''
        message = ''

        for index, row in temp_all.iterrows():
            if(row['username'] != str(request.user)):
                message = message + '<br> ' + row['query_name'] + ': {0} are not the owner of this track.</br>'.format(request.user)
                
            elif(row['repeat'] == 0):
                message = message + '<br>' + row['query_name'] + ': This task is already cancelled.</br>'

            else:
                message = message + '<br>' + row['query_name'] + ': Successfully cancelled.</br>'
                successes = successes + str(row['schedule_id']) +','
            


        if(successes):
            conn = engine.connect()
            print('DELETING tracks: ', successes[:-1])
            conn.execute("DELETE from django_q_schedule where id in ({0})".format(successes[:-1]))
            conn.close()
        
        engine.dispose()
        return render(request, 'tracker/create.html', {'status': message + successes + trackers})
    else:
        return render(request, 'tracker/create.html', {'status': 'ignore'})

@csrf_exempt
def create_track_ajax(request):
    tracker_created = False
    task_created = False
    error = 'None'
    if request.method == "POST":
        exists = Tracker.objects.filter(query_name__exact = request.POST.get('name'))
        if(exists):
            error = 'There is a track with the same name. Please change it.'
        else:
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
            except Exception as e:
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
                    frequency_level1 = frequency_level1,
                    minutes = frequency_level2,
                    repeats = repeat
                    )
            status = True
        except:
            status = False
    return status
    
@csrf_exempt
def get_tracks(request):
    engine = create_engine(db_connection_url)

    table = pd.read_sql_query("""
   
        select a.id, u.username, concat(query_name,'(id=',a.id::varchar(255),')') as query_name, query, frequency_level1, frequency_level2, fetch_size,
         case when coalesce(repeats,0) != 0 then 'Active' else 'Inactive' end status, date_start, date_end
        from tracker_tracker a
        inner join auth_user u on a.user_id = u.id
        left join django_q_schedule b on position(concat('''',a.query_name,'''') in b.kwargs) > 0 and b.func = 'tracker.tweet_collector.TweetCollector' 
        """, engine)
    engine.dispose()
    arr = []

    
    for index, row in table.iterrows():
        arr.append([row['id'], row['username'], row['query_name'], row['query'], row['frequency_level1'], row['frequency_level2'], 
                    row['fetch_size'], row['status'], row['date_start'], row['date_end']])
    return JsonResponse(arr, safe=False)
    
@csrf_exempt
def visualize_accumulations(request):
    trackers = request.POST.get('dummy')
    engine = create_engine(db_connection_url)
    temp_all = pd.read_sql_query("""
        select 
            a.query_name, 
            count(*) as total, 
            avg(case when replied_to_user is not null and retweeted_user is null and quoted_user is null then 1 else 0 end) as replied_to_perc,
            avg(case when replied_to_user is null and retweeted_user is not null and quoted_user is null then 1 else 0 end) as retweeted_perc,
            avg(case when replied_to_user is null and retweeted_user is null and quoted_user is not null then 1 else 0 end) as quoted_perc,
            avg(case when replied_to_user is null and retweeted_user is null and quoted_user is null then 1 else 0 end) as regular_perc
       from 
            tweet_main_table a
        where a.query_name in (
                select distinct query_name
                from tracker_tracker 
                where id in ({0}) 
            )
        group by
            a.query_name
        order by
            count(*) desc
        
        """.format(trackers), engine)

    date_all = pd.read_sql_query("""
        select 
            date(tweet_created_at) as query_name , count(*) as total 
        from 
            tweet_main_table 
        where query_name in (
                select distinct query_name
                from tracker_tracker 
                where id in ({0}) 
            )
        group by
            date(tweet_created_at)
        order by
            date(tweet_created_at)
        
        """.format(trackers), engine)

    print(temp_all.to_dict(orient='row'))

    engine.dispose()

    return JsonResponse({'counts': temp_all.to_dict(orient='row'), 'dates': date_all.to_dict(orient='row')})
    

    