from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
import sys
import ast
from sqlalchemy import create_engine
from django.conf import settings
import pandas as pd
import numpy as np 
import preprocessor as p
from .models import Processor_NLP
from django_q.tasks import async_task, schedule
from django_q.models import Schedule
import pickle
import uuid 
import nltk
from nltk.corpus import stopwords
nltk.download('stopwords')

db_connection_url = "postgresql://{}:{}@{}:{}/{}".format(
settings.DATABASES['default']['USER'],
settings.DATABASES['default']['PASSWORD'],
settings.DATABASES['default']['HOST'],
settings.DATABASES['default']['PORT'],
settings.DATABASES['default']['NAME'],
)

engine = create_engine(db_connection_url)

# Create your views here.

def show_dashboard(request):
    return render(request, 'analyzer/dashboard.html', {})
#ast(cast(a.tweet_created_at as Date) as varchar) 
@csrf_exempt
def get_basic_counts(request):
    table = pd.read_sql_query("""
        select cast(cast(a.tweet_created_at as Date) as varchar)  as date_info,
        coalesce(type, 'regular') as type_info, 
        count(*) total 
        from df_merge a  
        left join df_tweets_referenced b on a.key = b.key and a.tweet_tweet_id = b.tweet_id
        group by date_info, type_info
        """, engine)
    table = table.pivot(index="date_info", columns="type_info", values="total").reset_index()
    print(table)
    for var in table.columns:
        if(str(table[var].dtype) == 'int64'):
            table[var] = table[var].astype('object') 
  
    print('OLDU MU: ', table.dtypes)
    json_representation = {}
    for i in table.index:
        json_representation[i] = table.loc[i].to_dict()

    print(json_representation)
    return JsonResponse(json_representation)
 
@csrf_exempt
def get_domain_entity(request):
    table = pd.read_sql_query("""
       with base as (
            select distinct
                b.domain_name,  c.entity_name, count(*) as tot
            from 
                df_annotations as a, 
                (select distinct * from df_annotation_domain) as b, 
                (select distinct * from df_annotation_entity) as c
            where 
                a.domain_id = b.domain_id
                and a.entity_id = c.entity_id
            group by 
                b.domain_name,  c.entity_name
        ),
        base2 as (
            select *, row_number() over (partition by domain_name order by tot desc) as rc 
            from base 
        ),
        base3 as (select domain_name, sum(tot) as grand_tot from base group by domain_name order by grand_tot desc limit 10)
        select a.* from base2 a, base3 b where rc <= 10 and a.domain_name = b.domain_name order by a.domain_name, rc
        """, engine)
    print('+++++++++++++++++++++++++++++++++++++++++ AKSDPOAKSDPOAKSDPAKSOP')
    print(table)


    json_graph = []
    for domain in set(table['domain_name']):
        temp_dict ={}
        temp = table[table['domain_name'] == domain]
        temp_dict['name'] = domain
        temp_list = []
        for entity, tot in zip(temp['entity_name'], temp['tot']):
            
            temp_list.append({'name': entity, 'value': 1})
        temp_dict['children'] = temp_list
        json_graph.append(temp_dict)
    
 
    return JsonResponse(json_graph, safe=False)

    
@csrf_exempt
def get_domain_table(request):
    table = pd.read_sql_query("""select distinct domain_id, domain_name, domain_desc from df_annotation_domain""", engine)
    domains = []
    for index, row in table.iterrows():
        domains.append([row['domain_id'], row['domain_name'], row['domain_desc']])
    print(domains)
    return JsonResponse(domains, safe=False)

@csrf_exempt
def get_domain_for_graph(request):
    table = pd.read_sql_query("""
    with base as (select distinct domain_id, domain_name from df_annotation_domain)
    select domain_name, count(*) tot from df_annotations a, base b 
    where a.domain_id = b.domain_id
    group by domain_name 
    order by tot desc
    """, engine)
    domains = []
    for index, row in table.iterrows():
        domains.append({'domain': row['domain_name'], 'count':row['tot']})

    return JsonResponse(domains, safe=False)

@csrf_exempt
def get_entity_for_graph(request):
 
    table = pd.read_sql_query("""
    with 
    domain as (select distinct domain_id, domain_name from df_annotation_domain),
    entity as (select distinct entity_id, entity_name from df_annotation_entity where lower(entity_name) not like '%covid%' ),
    combined as (
        select concat(domain_name,': ', entity_name) as entity, count(*) tot from df_annotations a, domain b, entity c
        where a.domain_id = b.domain_id and a.entity_id = c.entity_id
        group by entity 
    )
    select * from combined  order by tot desc limit 100
    """, engine)
    entities = []
    print(table)
    for index, row in table.iterrows():
        entities.append({'entity':row['entity'], 'count':row['tot']})
    print(entities)
    return JsonResponse(entities, safe=False)

@csrf_exempt 
def get_entity_table(request):
    table = pd.read_sql_query("""select distinct a.entity_id, c.domain_name, a.entity_name, a.entity_desc from df_annotation_entity a
    inner join (select distinct domain_id, entity_id from df_annotations) b on a.entity_id = b.entity_id
    left join (select distinct domain_id, domain_name, domain_desc from df_annotation_domain) c on b.domain_id = c.domain_id""", engine)
    entities = []
    for index, row in table.iterrows():
        entities.append([row['entity_id'],  row['domain_name'], row['entity_name'], row['entity_desc']])
    return JsonResponse(entities, safe=False) 

@csrf_exempt 
def get_user_table(request):
    table = pd.read_sql_query("""
        with 
            base as (select id, count(*) tot from df_users group by id order by count(*)),
            base2 as (select *, row_number() over (order by tot desc) as rc from base)
        select
            a.id, a.username, max(a.description) as description, a.location, a.name, a.verified, max(rc) as rc
        from 
            df_users a, (select id, rc from base2 where rc <= 100) b 
        where
            a.id = b.id
		group by
			a.id, a.username, a.location, a.name, a.verified
 		order by
			max(rc)
    """, engine)
    users = []
    for index, row in table.iterrows():
        users.append([row['id'],  row['username'], row['rc'], row['description'], row['location'], row['name'], row['verified']])
    print(users)
    return JsonResponse(users, safe=False) 

@csrf_exempt 
def get_tracks(request):
    table = pd.read_sql_query("""
        select id, concat(query_name,'(id=',id::varchar(255),')') as query_name, query, frequency_level1, frequency_level2, fetch_size from tracker_tracker
    """, engine)
    tracks = []
    for index, row in table.iterrows():
        tracks.append([row['id'], row['query_name'],  row['query'], row['frequency_level1'], row['frequency_level2'], row['fetch_size']])

    return JsonResponse(tracks, safe=False) 
    

def domain_entity_analysis(request):
    return render(request, 'analyzer/domain_entity_analyzer.html')

def tweet_preprocessor(request):
    return render(request, 'analyzer/tweet_preprocessor.html')

def network_analyzer(request):
    return render(request, 'analyzer/network_analyzer.html')

@csrf_exempt 
def call_ajax(request):
    which = request.POST.get('which')

    if which == 'entity_domain_get_dates':
        arr = request.POST.get('data_sources')
        print(arr)
        if not arr:
            arr = 'null'
        table = pd.read_sql_query("""
            with 
                base as (select distinct query_name from tracker_tracker where id in ({0}))
            select distinct
                date(tweet_created_at) as collected_date
            from
                df_merge a, base b
            where
                a.query_name = b.query_name
            order by 
                collected_date
            """.format(arr), engine)
        print(table)
        dates  = []
        for dt in table['collected_date']:
            dates.append(dt)
        return JsonResponse({'dates': dates})
    elif which == 'get_domains':
        table = pd.read_sql_query("""select distinct domain_id, domain_name, domain_desc from df_annotation_domain""", engine)
        domains = []
        for index, row in table.iterrows():
            domains.append([row['domain_id'], row['domain_name'], row['domain_desc']])
        return JsonResponse(domains, safe=False)

    elif which == 'sentiment_analyzer':
        name = request.POST.get('name')
        tracker = request.POST.get('tracker')
        preproc = request.POST.get('preproc')
        stopwords = request.POST.get('stopwords')
        corrections = request.POST.get('corrections')
        
        if not tracker:
            arr = 'null'
        
        return create_preprocess_tweets_job(request.user, name, tracker, preproc, stopwords, corrections)

    elif which == 'processor_name_checker':
        status = 1
        name = request.POST.get('name')
        table = pd.read_sql_query("""select distinct name from analyzer_processor_nlp where name = '{0}' """.format(name), engine)
        if table.shape[0] > 0:
            status = 0

        return JsonResponse({'status':status})
    
    elif which == 'get_all_stopwords_files':
        sw_names, sw_default = get_all_stopwords_files()
        return JsonResponse({'sw_names': sw_names,
                             'sw_default': sw_default})

    elif which == 'get_all_corrections_files':
        cor_names = get_all_corrections_files()
        return JsonResponse({'cor_names': cor_names})

    elif which == 'save_stopwords':
        name = request.POST.get('name')
        sw = request.POST.get('sw')
        result = save_stopword(request.user, name, sw)
        
        return JsonResponse({'status': result})

    elif which == 'save_corrections':
        name = request.POST.get('name')
        cor = request.POST.get('cor')
        result = save_corrections(request.user, name, cor)
        
        return JsonResponse({'status': result})

    elif which == 'get_selected_stopwords':
        from nltk.corpus import stopwords
        name = request.POST.get('name')
        print('GETTİNG. ',name)
        if name == 'default_stopwords':
            return JsonResponse({'status':1, 'data': stopwords.words('english')})
        table = pd.read_sql_query("""select distinct file_url from analyzer_stopword_files where name ='{0}' """.format(name), engine)
        try:
            print(table['file_url'][0])
            obj = pd.read_pickle(table['file_url'][0])
            print(obj)
            return JsonResponse({'status': 1, 'data': obj})
        except:
            return JsonResponse({'status': 0, 'data': 0})

    elif which == 'get_selected_corrections':
         
        name = request.POST.get('name')
         
        table = pd.read_sql_query("""select distinct file_url from analyzer_corrections_files where name ='{0}' """.format(name), engine)
        try:
            print(table['file_url'][0])
            obj = pd.read_pickle(table['file_url'][0])
            to_javascript = ''
            print('***********************************************', type(obj))
            for row in obj:
                to_javascript = to_javascript + row[0] +' : ' + row[1] + '\n'
            return JsonResponse({'status': 1, 'data': to_javascript})
        except:
            return JsonResponse({'status': 0, 'data': 0})
    
    elif which == 'get_processors':
        print('GET PROCESSORS: ', request.user, request.user.id)
        
        table = pd.read_sql_query("""select id, name, tracker, stopwords, corrections, preproc from analyzer_processor_nlp where user_id ='{0}' """.format(request.user.id), engine)
        procs = []
        for index, row in table.iterrows():
            procs.append([row['id'], row['name'],  row['tracker'], row['stopwords'], row['corrections'], row['preproc']])
            print('YES')
        print(procs)
        return JsonResponse(procs, safe=False) 


            
    elif which == 'get_chord_chart_data_for_domains':
        table = pd.read_sql_query("""
            with base as (
                select distinct tweet_id, domain_name 
                from df_annotations a, (select distinct domain_id, domain_name from df_annotation_domain) b 
                where a.domain_id = b.domain_id
            )
            select a.domain_name as from, b.domain_name as to, count(*) as value    
            from base a,  base b
            where a.tweet_id = b.tweet_id and a.domain_name < b.domain_name
            group by a.domain_name, b.domain_name
         """, engine)
        return JsonResponse({'data':table.to_dict(orient='records')})
    
    elif which == 'get_chord_chart_data_for_domains2':
        #temp = pd.read_sql_query("""
        #    select a.domain_id as id, domain_name as label, count(*) as value 
        #    from df_annotations a, (select distinct domain_id, domain_name from df_annotation_domain) b 
        #    where a.domain_id = b.domain_id
        #    group by a.domain_id, domain_name
        # """, engine)
        
        temp2 = pd.read_sql_query("""
            with base as (
                select lower(normalized_text) as label, count(distinct a.tweet_id) as value 
                from df_entities a, (select tweet_id, count(distinct lower(normalized_text)) as tot from df_entities where category = 'annotations'  and query_name ='news_global'  group by tweet_id having count(*) >= 3) b
                where a.tweet_id = b.tweet_id and category = 'annotations' and query_name ='news_global'
                group by lower(normalized_text) having count(*) >= 1
            ),
            base2 as (
                select 
                    *,
                    row_number() over (order by label) as id
                from 
                    base
            ),
            base3 as (
                select 
                    lower(a.normalized_text) as _from, lower(b.normalized_text) as _to, count(*) as tot
                from 
                    df_entities a
                inner join 
                    df_entities b on a.tweet_id = b.tweet_id and b.category = 'annotations' and lower(a.normalized_text) < lower(b.normalized_text)
                where 
                    a.category = 'annotations' and a.query_name ='news_global' and b.query_name ='news_global'
                group by 
                    lower(a.normalized_text), lower(b.normalized_text)
            )
            select b.id as from, c.id as to, tot as value
            from base3 a, base2 b, base2 c
            where a._from = b.label and a._to = c.label
            
        limit 200""", engine)

        temp = pd.read_sql_query("""
            with base as (
                select lower(normalized_text) as label, count(distinct a.tweet_id) as value 
                from df_entities a, (select tweet_id, count(distinct lower(normalized_text)) as tot from df_entities where category = 'annotations' and  query_name ='news_global'  group by tweet_id having count(*) >= 3) b
                where a.tweet_id = b.tweet_id and category = 'annotations' and query_name ='news_global'
                group by lower(normalized_text) having count(*) >= 1
            )
            select 
                *,
                row_number() over (order by label) as id
            from 
	            base
         """, engine)

        return JsonResponse({'data':temp.to_dict(orient='records'), 'data2':temp2.to_dict(orient='records')})

    elif which == 'get_word_freqs_and_bigrams_for_check':
        import collections
        ids = request.POST.get('selected')
        temp = pd.read_sql_query("""
                with base as (select distinct name from analyzer_processor_nlp where id in ({0}))
                select tweet_text from df_tweets_processed a, base b where a.processor_name = b.name

                """.format(ids), engine)
        name = pd.read_sql_query("""select distinct name from analyzer_processor_nlp where id in ({0})""".format(ids), engine)
        

        words = pd.Series(' '.join(temp.tweet_text).split()).value_counts()[:1000].rename_axis('word').reset_index(name='count')
        arr = []
        for index, row in words.iterrows():
            arr.append([name['name'][0], row['word'], row['count']])

        bigram = []
        res = [(x +' '+ i.split()[j + 1]) for i in temp['tweet_text'] for j, x in enumerate(i.split()) if j < len(i.split()) - 1] 
        res = collections.Counter(res)
        res = res.most_common(1000)
        
        for item in res:
            bigram.append([name['name'][0], item[0], item[1]]) 
        
        return JsonResponse({'word_count': arr, 'bigram': bigram})  
       
    elif which == 'get_images':
        temp = pd.read_sql_query("""
                select url, count(*) as total from df_media
                where type = 'photo'
                group by url
                
                having count(*) >= 10
                order by count(*) desc
                """, engine)
        print(temp.to_dict(orient='records'))
        return JsonResponse(temp.to_dict(orient='records'), safe=False)

def save_stopword(user, name, sw):
    stopwords_file = '/usr/src/mainapp/' + name + '.pckl'
    try:
        record = {}
        stopwords = sw.split('\n')
        print(sw, stopwords, stopwords_file)
 
        with open(stopwords_file, 'wb') as f:
            pickle.dump(stopwords, f)
        record['user'] = str(user)
        record['name'] = name
        record['file_url'] = stopwords_file
        df = pd.DataFrame(record, index=[0])
        print(df)
        df.to_sql('analyzer_stopword_files', engine, if_exists='append', index=False)
        return 1
    except Exception as e:
        print(e)
        return 0


def save_corrections(user, name, cor):
    cor_file = '/usr/src/mainapp/' + name + '.pckl'
    print('***********************************************', cor, ast.literal_eval(cor), type(ast.literal_eval(cor)))
    try:
        record = {}
        corrections = ast.literal_eval(cor)
        
        with open(cor_file, 'wb') as f:
            pickle.dump(corrections, f)
        record['user'] = str(user)
        record['name'] = name
        record['file_url'] = cor_file
        df = pd.DataFrame(record, index=[0])
        print(df)
        df.to_sql('analyzer_corrections_files', engine, if_exists='append', index=False)
        return 1
    except Exception as e:
        print(e)
        return 0
    


def get_all_stopwords_files():
    files = ['default_stopwords']
    try:
        
        table = pd.read_sql_query("""select distinct name from analyzer_stopword_files """, engine)
        for sw in table['name']:
            files.append(sw)
    except:
        print('///////////////////////////////////////////////// stopwords table not exist!')
    sw_default = stopwords.words('english')
    return(files, sw_default)


def get_all_corrections_files():
    files = []
    try:
        
        table = pd.read_sql_query("""select distinct name from analyzer_corrections_files """, engine)
        for cor in table['name']:
            files.append(cor)
    except:
        print('///////////////////////////////////////////////// stopwords table not exist!')
    return(files)
        


def create_preprocess_tweets_job(user, name, tracker, preproc, stopwords, corrections):
    print(tracker,tracker,tracker,tracker,tracker,tracker,tracker,tracker,tracker,tracker,tracker,tracker,tracker,tracker,tracker)
    sw = True
    cor = True
    
    preproc = preproc.split(',')

    Processor_NLP.objects.create(user=user,
                                name=name,
                                tracker=tracker,
                                preproc=preproc,
                                stopwords=stopwords,
                                corrections=corrections)

    schedule('analyzer.nlp_processor.Processor',
                    user_name=str(user),
                    proc_name=name,
                    tracker=tracker,
                    preproc=preproc,
                    stopwords_file=stopwords,
                    corrections_file=corrections,
                    schedule_type='I',
                    minutes = 1,
                    repeats = 100000000
                    )
    
    return JsonResponse({'status': str(user)})
       

def tweet_preprocessor_delete(request):
    if(request.method == "POST"):
        ids = request.POST.get('dummy')
        try:
            conn = engine.connect()
            print('DELETING ', ids)
            conn.execute("DELETE from analyzer_processor_nlp where id in ({0})".format(ids))
            return render(request, 'analyzer/tweet_preprocessor.html', {'result':'OK'})
        except Exception as e:
            
            return render(request, 'analyzer/tweet_preprocessor.html', {'result':str(e)})
   
def tweet_media_analyzer(request):
    return render(request, 'analyzer/tweet_media_analyzer.html')


