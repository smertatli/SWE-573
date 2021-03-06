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

import networkx as nx

db_connection_url = "postgresql://{}:{}@{}:{}/{}".format(
settings.DATABASES['default']['USER'],
settings.DATABASES['default']['PASSWORD'],
settings.DATABASES['default']['HOST'],
settings.DATABASES['default']['PORT'],
settings.DATABASES['default']['NAME'],
)



# Create your views here.

def show_dashboard(request):
    return render(request, 'analyzer/dashboard.html', {})
#ast(cast(a.tweet_created_at as Date) as varchar) 
@csrf_exempt
def get_basic_counts(request):
    engine = create_engine(db_connection_url)
    table = pd.read_sql_query("""
        select cast(cast(a.tweet_created_at as Date) as varchar)  as date_info,
        coalesce(type, 'regular') as type_info, 
        count(*) total 
        from df_merge a  
        left join df_tweets_referenced b on a.key = b.key and a.tweet_tweet_id = b.tweet_id
        group by date_info, type_info
        """, engine)
    engine.dispose()
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
    engine = create_engine(db_connection_url)
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
    engine.dispose()
  
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
    engine = create_engine(db_connection_url)
    table = pd.read_sql_query("""select distinct domain_id, domain_name, domain_desc from df_annotation_domain""", engine)
    domains = []
    for index, row in table.iterrows():
        domains.append([row['domain_id'], row['domain_name'], row['domain_desc']])
    print(domains)
    engine.dispose()
    return JsonResponse(domains, safe=False)

@csrf_exempt
def get_domain_for_graph(request):
    engine = create_engine(db_connection_url)
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
    engine.dispose()
    return JsonResponse(domains, safe=False)

@csrf_exempt
def get_entity_for_graph(request):
    engine = create_engine(db_connection_url)
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
    engine.dispose()
    return JsonResponse(entities, safe=False)

@csrf_exempt 
def get_entity_table(request):
    engine = create_engine(db_connection_url)
    table = pd.read_sql_query("""select distinct a.entity_id, c.domain_name, a.entity_name, a.entity_desc from df_annotation_entity a
    inner join (select distinct domain_id, entity_id from df_annotations) b on a.entity_id = b.entity_id
    left join (select distinct domain_id, domain_name, domain_desc from df_annotation_domain) c on b.domain_id = c.domain_id""", engine)
    entities = []
    for index, row in table.iterrows():
        entities.append([row['entity_id'],  row['domain_name'], row['entity_name'], row['entity_desc']])
    engine.dispose()
    return JsonResponse(entities, safe=False) 

@csrf_exempt 
def get_user_table(request):
    engine = create_engine(db_connection_url)
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
    engine.dispose()
    return JsonResponse(users, safe=False) 

@csrf_exempt 
def get_tracks(request):
    engine = create_engine(db_connection_url)
    table = pd.read_sql_query("""
        select id, concat(query_name,'(id=',id::varchar(255),')') as query_name, query, frequency_level1, frequency_level2, fetch_size from tracker_tracker
    """, engine)
    tracks = []
    for index, row in table.iterrows():
        tracks.append([row['id'], row['query_name'],  row['query'], row['frequency_level1'], row['frequency_level2'], row['fetch_size']])
    engine.dispose()
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
    engine = create_engine(db_connection_url)
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
                tweet_main_table a, base b
            where
                a.query_name = b.query_name
            order by 
                collected_date
            """.format(arr), engine)
        print(table)
        dates  = []
        for dt in table['collected_date']:
            dates.append(dt)
        engine.dispose()
        return JsonResponse({'dates': dates})
    if which == 'get_processor_dates':
        arr = request.POST.get('processors')
        print(arr)
        if not arr:
            arr = 'null'
        table = pd.read_sql_query("""
            select distinct
                date(a.created_at) as collected_date
            from 
                df_tweets_processed a, analyzer_processor_nlp b
            where 
                a.processor_name = b.name and b.id in ({0}) 
            order by
                1 
            """.format(arr), engine)
        print(table)
        dates  = []
        for dt in table['collected_date']:
            dates.append(dt)
        engine.dispose()
        return JsonResponse({'dates': dates})
    elif which == 'get_domains':
        table = pd.read_sql_query("""select distinct domain_id, domain_name, domain_desc from df_annotation_domain""", engine)
        domains = []
        for index, row in table.iterrows():
            domains.append([row['domain_id'], row['domain_name'], row['domain_desc']])

        engine.dispose()
        return JsonResponse(domains, safe=False)

    elif which == 'sentiment_analyzer':
        name = request.POST.get('name')
        tracker = request.POST.get('tracker')
        preproc = request.POST.get('preproc')
        nlp = request.POST.get('nlp')
        stopwords = request.POST.get('stopwords')
        corrections = request.POST.get('corrections')
        if not tracker:
            arr = 'null'
        engine.dispose()
        return create_preprocess_tweets_job(request.user, name, tracker, preproc, nlp, stopwords, corrections)

    elif which == 'processor_name_checker':
        status = 1
        name = request.POST.get('name')
        table = pd.read_sql_query("""select distinct name from analyzer_processor_nlp where name = '{0}' """.format(name), engine)
        if table.shape[0] > 0:
            status = 0
        engine.dispose()
        return JsonResponse({'status':status})
    
    elif which == 'get_all_stopwords_files':
        sw_names, sw_default = get_all_stopwords_files()
        engine.dispose()
        return JsonResponse({'sw_names': sw_names,
                             'sw_default': sw_default})

    elif which == 'get_all_corrections_files':
        cor_names = get_all_corrections_files()
        engine.dispose()
        return JsonResponse({'cor_names': cor_names})

    elif which == 'save_stopwords':
        name = request.POST.get('name')
        sw = request.POST.get('sw')
        result = save_stopword(request.user, name, sw)
        engine.dispose()
        return JsonResponse({'status': result})

    elif which == 'save_corrections':
        name = request.POST.get('name')
        cor = request.POST.get('cor')
        result = save_corrections(request.user, name, cor)
        engine.dispose()
        return JsonResponse({'status': result})

    elif which == 'get_selected_stopwords':
        from nltk.corpus import stopwords
        name = request.POST.get('name')
        print('GETTİNG. ',name)
        if name == 'default_stopwords':
            engine = create_engine(db_connection_url)
            return JsonResponse({'status':1, 'data': stopwords.words('english')})
        table = pd.read_sql_query("""select distinct file_url from analyzer_stopword_files where name ='{0}' """.format(name), engine)
        try:
            print(table['file_url'][0])
            obj = pd.read_pickle(table['file_url'][0])
            print(obj)
            engine.dispose()
            return JsonResponse({'status': 1, 'data': obj})
        except:
            engine.dispose()
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
            engine.dispose()
            return JsonResponse({'status': 1, 'data': to_javascript})
            
        except:
            engine.dispose()
            return JsonResponse({'status': 0, 'data': 0})
        
    
    elif which == 'get_processors':
        print('GET PROCESSORS: ', request.user, request.user.id)
        
        table = pd.read_sql_query("""
            select a.id, a.name, a.tracker, a.stopwords, a.corrections, a.preproc, a.nlp, case when b.id is not null then 'Active' else 'Inactive' end status
            from analyzer_processor_nlp a left join django_q_schedule b on position(concat('''',a.name,'''')  in b.kwargs) > 0 and coalesce(repeats,0) <> 0
            and func = 'analyzer.nlp_processor.Processor'
             
            """.format(request.user.id), engine)
        procs = []
        for index, row in table.iterrows():
            procs.append([row['id'], row['name'],  row['tracker'], row['stopwords'], row['corrections'], row['preproc'], row['nlp'], row['status']])
        engine.dispose()
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
        engine.dispose()
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
        engine.dispose()
        return JsonResponse({'data':temp.to_dict(orient='records'), 'data2':temp2.to_dict(orient='records')})

    elif which == 'get_word_freqs_and_bigrams_for_check':
        import collections
        import random
        ids = request.POST.get('selected')
        rand = random.randint(0,4)
        print('selecting for:', str(rand), ids)
        tracker_ids = pd.read_sql_query('select tracker from analyzer_processor_nlp where id in ({0})'.format(ids), engine)
        total_count = 0
        print('second....')
        if not tracker_ids.empty:
            total_count = pd.read_sql_query("""select count(*) tot from tweet_main_table 
                          where query_name in (select query_name from tracker_tracker where id in ({0}))""".format(tracker_ids['tracker'][0]), engine)
        print('third....')
        total = pd.read_sql_query("""
                with base as (select distinct name from analyzer_processor_nlp where id in ({0}))
                SELECT count(*) as total_processed, count(distinct coalesce(retweeted_tweet_id, tweet_tweet_id)) as total_compressed, {1} as total_collected
                FROM   df_tweets_processed t, base b
                where t.processor_name = b.name  
                """.format(ids, total_count['tot'][0] if not total_count.empty else total_count), engine)
        print('fourth....')
        if not total.empty:
            total = total.melt(var_name="funnel", value_name="count")
            total = total.sort_values(by=['count'], ascending=False)
        print('6th....')
        word_cnt_dist = pd.read_sql_query("""
                with base as (select distinct name from analyzer_processor_nlp where id in ({0}))
                SELECT ((array_length(regexp_split_to_array(tweet_text, '\s+'), 1))::float / 5)::int*5 as bucket, count(*) as total
                FROM   df_tweets_processed t, base b
                where t.processor_name = b.name  
                group by bucket
                order by bucket
                """.format(ids, rand), engine)
        print('7th....')
        length_dist = pd.read_sql_query("""
                with base as (select distinct name from analyzer_processor_nlp where id in ({0}))
                SELECT (length(tweet_text)::float / 10)::int*10 as bucket, count(*) as total
                FROM   df_tweets_processed t, base b
                where t.processor_name = b.name  
                group by bucket
                order by bucket
                """.format(ids), engine)
        print('8th....')
        word = pd.read_sql_query("""
                with base as (select distinct name from analyzer_processor_nlp where id in ({0}))
                SELECT b.name, elem,count(distinct tweet_Tweet_id) as freq
                FROM   df_tweets_processed t, base b,
                unnest(string_to_array(t.tweet_text, ' ')) WITH ORDINALITY a(elem, nr)  
                where t.processor_name = b.name and elem > '' and tweet_tweet_id::bigint %% 5 = {1} 
                group by b.name, elem
                order by 3 desc
                limit 1000
                """.format(ids, rand), engine)
        print('9th....')
        polarity_dist = pd.read_sql_query("""
                with base as (select distinct name from analyzer_processor_nlp where id in ({0}))
                select 
                ((coalesce(polarity,0)*10)::int) /10::float as severity, count(*) as total
                FROM   df_tweets_processed t, base b
                where t.processor_name = b.name 
                group by severity
                order by severity
                """.format(ids), engine)
        print('10th....')
        subjectivity_dist = pd.read_sql_query("""
                with base as (select distinct name from analyzer_processor_nlp where id in ({0}))
                select 
                ((subjectivity*10)::int) /10::float as severity, count(*) as total
                FROM   df_tweets_processed t, base b
                where t.processor_name = b.name 
                group by severity
                order by severity
                """.format(ids), engine)
        print('11th....')
        print('calculating bigram freqs')
        bigram = pd.read_sql_query("""
                with proc as (select distinct name from analyzer_processor_nlp where id in ({0})),
                base as (
                    SELECT b.name,tweet_Tweet_id, elem, nr, lag(elem) over (partition by tweet_tweet_id order by nr) as elem2
                    FROM   df_tweets_processed t,  proc b,
                    unnest(string_to_array(t.tweet_text, ' ')) WITH ORDINALITY a(elem, nr)
                    where t.processor_name = b.name and tweet_tweet_id::bigint %% 5 = {1} 
                )
                select name, concat(elem, ' ', elem2) as bigram, count(distinct tweet_Tweet_id) as freq 
                from base
                where elem <> '' and elem2 <> ''
                group by name, concat(elem, ' ', elem2) 
                order by count(distinct tweet_Tweet_id) desc 
                limit 1000
                """.format(ids, rand), engine)
        print('12th....')
        word_arr = []
        for index, row in word.iterrows():
            word_arr.append([row[0], row[1], row[2]]) 
        print('13th....')
        bigram_arr = []
        for index, row in bigram.iterrows():
            bigram_arr.append([row[0], row[1], row[2]]) 
        engine.dispose()
        print('14th....')
        return JsonResponse({'word_count': word_arr, 'bigram': bigram_arr, 'total': total.to_dict(orient='records'), 
                             'word_cnt_dist':word_cnt_dist.to_dict(orient='records'),
                             'length_dist': length_dist.to_dict(orient='records'),
                             'polarity_dist': polarity_dist.to_dict(orient='records'),
                             'subjectivity_dist': subjectivity_dist.to_dict(orient='records')})  
       
    elif which == 'get_images':
        temp = pd.read_sql_query("""
                select url, count(*) as total from df_media
                where type = 'photo'
                group by url
                
                having count(*) >= 10
                order by count(*) desc
                """, engine)
        print(temp.to_dict(orient='records'))
        engine.dispose()
        return JsonResponse(temp.to_dict(orient='records'), safe=False)

    elif which == 'get_network_data':

        track = request.POST.get('track')
        domain = request.POST.get('domain')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        node_level = request.POST.get('node_level')
        processor = request.POST.get('processor')
        top_n = request.POST.get('top_n')
        exclude = request.POST.get('excluded_terms')
        excluded_terms = ''
        for elem in exclude.split('\n'):
            excluded_terms = excluded_terms + "'" + elem.strip() + "',"
        excluded_terms = excluded_terms[:-1]
        
        if not domain:
            domain =''
        temp = ''
        if node_level == 'domain':
            if domain == '':
                temp = pd.read_sql_query(""" 
                    with base as (
                        select distinct
                            t.tweet_Tweet_id, 
                            split_part(elem, '=', 1) as domain
                        from 
                            tweet_main_table t, tracker_tracker b, 
                            unnest(string_to_array(t.domain_entities, ' || ')) WITH ORDINALITY a(elem, nr)
                        where
                            b.id in ({0}) and b.query_name = t.query_name and date(tweet_created_at) between '{1}' and '{2}'
                    ),
                    ids as (
                        select domain, count(*) node_size from base group by domain
                    ),
                    ids2 as (
                        select *, row_number() over (order by node_size desc) as id from ids
                    )
                    select 
                        a.domain as from_name, id1.id as from,  id1.node_size as from_size, 
                        b.domain as to_name,  id2.id as to,  id2.node_size as to_size,  
                        count(*) as value
                    from base a, base b, ids2 id1, ids2 id2
                    where a.tweet_Tweet_id=b.tweet_Tweet_id and a.domain < b.domain and a.domain = id1.domain and b.domain=id2.domain
                    and a.domain not in ({4}) and b.domain not in ({4})
                    group by a.domain, b.domain, id1.id, id2.id, id1.node_size, id2.node_size 
                    order by count(*) desc
                    limit {3}
                """.format(track, start_date, end_date, str(100) if top_n == '' else str(top_n) , excluded_terms), engine)
            else:
                temp = pd.read_sql_query(""" 
                    with 
                    domains as (
                        select domain_id, max(domain_name) as domain_name from df_annotation_domain group by domain_id
                    ),
                    base as (
                        select distinct
                            t.tweet_Tweet_id
                        from 
                            tweet_main_table t, tracker_tracker b, domains c,
                            unnest(string_to_array(t.domain_entities, ' || ')) WITH ORDINALITY a(elem, nr)
                        where
                            b.id in ({0}) and b.query_name = t.query_name and split_part(elem, '=', 1) = lower(c.domain_name)
                            and c.domain_id::int in ({3}) and date(tweet_created_at) between '{1}' and '{2}'
                        
                    ),
                    base2 as (
                        select distinct
                            t.tweet_Tweet_id, 
                            split_part(elem, '=', 1) as domain
                        from 
                            tweet_main_table t, tracker_tracker b, domains c, base d,
                            unnest(string_to_array(t.domain_entities, ' || ')) WITH ORDINALITY a(elem, nr)
                        where
                            b.id in ({0}) and b.query_name = t.query_name and split_part(elem, '=', 1) = lower(c.domain_name)
                            and c.domain_id::int not in ({3}) and d.tweet_Tweet_id = t.tweet_Tweet_id
                            and a.domain not in ({5}) and b.domain not in ({5})
                    ),
                    ids as (
                        select domain, count(*) node_size from base2 group by domain
                    ),
                    ids2 as (
                        select *, row_number() over (order by node_size desc) as id from ids
                    )
                    select 
                        a.domain as from_name, id1.id as from,  id1.node_size as from_size, 
                        b.domain as to_name,  id2.id as to,  id2.node_size as to_size,  
                        count(*) as value
                    from base2 a, base2 b, ids2 id1, ids2 id2
                    where a.tweet_Tweet_id=b.tweet_Tweet_id and a.domain < b.domain and a.domain = id1.domain and b.domain=id2.domain
                    group by a.domain, b.domain, id1.id, id2.id, id1.node_size, id2.node_size 
                    order by count(*) desc
                    limit {4}
                """.format(track, start_date, end_date, domain, str(100) if top_n == '' else str(top_n), excluded_terms), engine)

            distinct, degree_df, bet_df, eigen, clustering = get_network_metrics(temp)

            engine.dispose()
            return JsonResponse({'data': temp[['from', 'to', 'value']].to_dict(orient='records'), 'data2': distinct.to_dict(orient='records'),
                                                'degree_df': degree_df.to_json(orient='records'),
                                                'bet_df': bet_df.to_json(orient='records'),
                                                'ieg_df': eigen.to_json(orient='records'),
                                                'clus_df': clustering.to_json(orient='records')})


        elif node_level == 'entity':
            if domain != '':
                temp = pd.read_sql_query("""
                    with 
                    domains as (
                        select domain_id, max(domain_name) as domain_name from df_annotation_domain group by domain_id
                    ),
                    base as (
                        select distinct
                            t.tweet_Tweet_id, lower(domain_name) as domain_name
                        from 
                            tweet_main_table t, tracker_tracker b, domains d,
                            unnest(string_to_array(t.domain_entities, ' || ')) WITH ORDINALITY a(elem, nr)
                        where
                            b.id in ({0}) and b.query_name = t.query_name 
                            and split_part(elem, '=', 1) = lower(d.domain_name)
                            and d.domain_id::bigint in ({3})
                            and date(tweet_created_at) between '{1}' and '{2}'
                    ),
                    base2 as (
                        select distinct
                            t.tweet_Tweet_id, 
                            split_part(elem, '=', 2) as entity
                        from 
                            tweet_main_table t, base d,
                            unnest(string_to_array(t.domain_entities, ' || ')) WITH ORDINALITY a(elem, nr)
                        where
                            split_part(elem, '=', 1) = domain_name and
                            d.tweet_Tweet_id = t.tweet_Tweet_id
                            and split_part(elem, '=', 2) not in ({5})
                    ),
                    ids as (
                        select entity, count(*) node_size from base2 group by entity
                    ),
                    ids2 as (
                        select *, row_number() over (order by node_size desc) as id from ids
                    )
                    select 
                        a.entity as from_name, id1.id as from,  id1.node_size as from_size, 
                        b.entity as to_name,  id2.id as to,  id2.node_size as to_size,  
                        count(*) as value
                    from base2 a, base2 b, ids2 id1, ids2 id2
                    where a.tweet_Tweet_id=b.tweet_Tweet_id and a.entity < b.entity and a.entity = id1.entity and b.entity=id2.entity
                    group by a.entity, b.entity, id1.id, id2.id, id1.node_size, id2.node_size 
                    order by count(*) desc
                    limit {4}
                """.format(track, start_date, end_date, domain, str(100) if top_n == '' else str(top_n), excluded_terms ), engine)
            else:
                temp = pd.read_sql_query("""
                   with 
                    base as (
                        select distinct
                            t.tweet_Tweet_id, lower(split_part(elem, '=', 2)) as entity
                        from 
                            tweet_main_table t, tracker_tracker b, 
                            unnest(string_to_array(t.domain_entities, ' || ')) WITH ORDINALITY a(elem, nr)
                        where
                            b.id in ({0}) and b.query_name = t.query_name and date(tweet_created_at) between '{1}' and '{2}'
                            and split_part(elem, '=', 2) not in ({4})
                    ),
                    ids as (
                        select entity, count(*) node_size from base group by entity
                    ),
                    ids2 as (
                        select *, row_number() over (order by node_size desc) as id from ids
                    )
                    select 
                        a.entity as from_name, id1.id as from,  id1.node_size as from_size, 
                        b.entity as to_name,  id2.id as to,  id2.node_size as to_size,  
                        count(*) as value
                    from base a, base b, ids2 id1, ids2 id2
                    where a.tweet_Tweet_id=b.tweet_Tweet_id and a.entity < b.entity and a.entity = id1.entity and b.entity=id2.entity
                    group by a.entity, b.entity, id1.id, id2.id, id1.node_size, id2.node_size 
                    order by count(*) desc
                    limit {3}
                    """.format(track, start_date, end_date, str(100) if top_n == '' else str(top_n), excluded_terms ), engine)



            distinct, degree_df, bet_df, eigen, clustering = get_network_metrics(temp)

            engine.dispose()
            return JsonResponse({'data': temp[['from', 'to', 'value']].to_dict(orient='records'), 'data2': distinct.to_dict(orient='records'),
                                                'degree_df': degree_df.to_json(orient='records'),
                                                'bet_df': bet_df.to_json(orient='records'),
                                                'ieg_df': eigen.to_json(orient='records'),
                                                'clus_df': clustering.to_json(orient='records')})

        elif node_level == 'entity_tagme':
            try:
                temp = pd.read_sql_query("""
                with 
                    base as (
                        select distinct
                            t.tweet_Tweet_id, lower(split_part(elem, '=', 2)) as entity
                        from 
                            tweet_tagme_annotation t, tracker_tracker b, tweet_main_Table c,
                            unnest(string_to_array(t.annotations, '||')) WITH ORDINALITY a(elem, nr)
                        where
                            b.id in ({0}) and b.query_name = c.query_name and date(c.tweet_created_at) between '{1}' and '{2}'
                            and split_part(elem, '=', 2) not in ({4})
                            and t.tweet_tweet_id = c.tweet_tweet_id
                    ),
                    ids as (
                        select entity, count(*) node_size from base group by entity
                    ),
                    ids2 as (
                        select *, row_number() over (order by node_size desc) as id from ids
                    )
                    select 
                        a.entity as from_name, id1.id as from,  id1.node_size as from_size, 
                        b.entity as to_name,  id2.id as to,  id2.node_size as to_size,  
                        count(*) as value
                    from base a, base b, ids2 id1, ids2 id2
                    where a.tweet_Tweet_id=b.tweet_Tweet_id and a.entity < b.entity and a.entity = id1.entity and b.entity=id2.entity 
                    and a.entity > '' and b.entity > ''
                    group by a.entity, b.entity, id1.id, id2.id, id1.node_size, id2.node_size 
                    order by count(*) desc
                    limit {3}
                    """.format(track, start_date, end_date, str(100) if top_n == '' else str(top_n), excluded_terms ), engine)

            except Exception as e:
                print('ERROR IN DOMAIN TAGME NETWORK: ', str(e))

            distinct, degree_df, bet_df, eigen, clustering = get_network_metrics(temp)

            engine.dispose()
            return JsonResponse({'data': temp[['from', 'to', 'value']].to_dict(orient='records'), 'data2': distinct.to_dict(orient='records'),
                                                'degree_df': degree_df.to_json(orient='records'),
                                                'bet_df': bet_df.to_json(orient='records'),
                                                'ieg_df': eigen.to_json(orient='records'),
                                                'clus_df': clustering.to_json(orient='records')})
        elif node_level == 'hashtag':
            if domain == '':
                temp = pd.read_sql_query("""
                            with 
                            base as (
                                select distinct
                                    t.tweet_Tweet_id, lower(elem) as tag
                                from 
                                    tweet_main_table t, tracker_tracker b, 
                                    unnest(string_to_array(t.hashtags, '||')) WITH ORDINALITY a(elem, nr)
                                where
                                    b.id in ({0}) and b.query_name = t.query_name and date(tweet_created_at) between '{1}' and '{2}'
                                    and lower(elem) not in ({4})
                            ),
                            ids as (
                                select tag, count(*) node_size from base group by tag
                            ),
                            ids2 as (
                                select *, row_number() over (order by node_size desc) as id from ids
                            )
                            select 
                                a.tag as from_name, id1.id as from,  id1.node_size as from_size, 
                                b.tag as to_name,  id2.id as to,  id2.node_size as to_size,  
                                count(*) as value
                            from base a, base b, ids2 id1, ids2 id2
                            where a.tweet_Tweet_id=b.tweet_Tweet_id and a.tag < b.tag and a.tag = id1.tag and b.tag=id2.tag
                            group by a.tag, b.tag, id1.id, id2.id, id1.node_size, id2.node_size 
                            order by count(*) desc
                            limit {3}
                        """.format(track, start_date, end_date, str(100) if top_n == '' else str(top_n), excluded_terms ),engine)
            else:
                temp = pd.read_sql_query("""
                            with 
                            domains as (
                                select domain_id, max(domain_name) as domain_name from df_annotation_domain group by domain_id
                            ),
                            base as (
                                select distinct
                                    t.tweet_Tweet_id
                                from 
                                    tweet_main_table t, tracker_tracker b, domains d,
                                    unnest(string_to_array(t.domain_entities, ' || ')) WITH ORDINALITY a(elem, nr)
                                where
                                    b.id in ({0}) and b.query_name = t.query_name 
                                    and split_part(elem, '=', 1) = lower(d.domain_name)
                                    and d.domain_id::bigint in ({3})
                                    and date(tweet_created_at) between '{1}' and '{2}'
                            ),
                            base2 as (
                                select distinct
                                    t.tweet_Tweet_id, 
                                    lower(elem) as tag
                                from 
                                    tweet_main_table t, base d,
                                    unnest(string_to_array(t.hashtags, '||')) WITH ORDINALITY a(elem, nr)
                                where
                                    d.tweet_Tweet_id = t.tweet_Tweet_id
                                    and lower(elem) not in ({5})
                            ),
                            ids as (
                                select tag, count(*) node_size from base2 group by tag
                            ),
                            ids2 as (
                                select *, row_number() over (order by node_size desc) as id from ids
                            )
                            select 
                                a.tag as from_name, id1.id as from,  id1.node_size as from_size, 
                                b.tag as to_name,  id2.id as to,  id2.node_size as to_size,  
                                count(*) as value
                            from base2 a, base2 b, ids2 id1, ids2 id2
                            where a.tweet_Tweet_id=b.tweet_Tweet_id and a.tag < b.tag and a.tag = id1.tag and b.tag=id2.tag
                            group by a.tag, b.tag, id1.id, id2.id, id1.node_size, id2.node_size 
                            order by count(*) desc
                            limit {4}
                        """.format(track, start_date, end_date, domain, str(100) if top_n == '' else str(top_n), excluded_terms ),engine)
    
            distinct, degree_df, bet_df, eigen, clustering = get_network_metrics(temp)

            engine.dispose()
            return JsonResponse({'data': temp[['from', 'to', 'value']].to_dict(orient='records'), 'data2': distinct.to_dict(orient='records'),
                                                'degree_df': degree_df.to_json(orient='records'),
                                                'bet_df': bet_df.to_json(orient='records'),
                                                'ieg_df': eigen.to_json(orient='records'),
                                                'clus_df': clustering.to_json(orient='records')})
  
        elif node_level == 'mention':
            if domain != '':
                temp = pd.read_sql_query("""
                           with 
                            domains as (
                                select domain_id, max(domain_name) as domain_name from df_annotation_domain group by domain_id
                            ),
                            base as (
                                select distinct
                                    t.tweet_Tweet_id
                                from 
                                    tweet_main_table t, tracker_tracker b, domains d,
                                    unnest(string_to_array(t.domain_entities, '||')) WITH ORDINALITY a(elem, nr)
                                where
                                    b.id in ({0}) and b.query_name = t.query_name 
                                    and split_part(elem, '=', 1) = lower(d.domain_name)
                                    and d.domain_id::bigint in ({3})
                                    and date(tweet_created_at) between '{1}' and '{2}'
                                    
                            ),
                            base2 as (
                                select distinct
                                    t.tweet_Tweet_id, username as from_user,
                                    lower(elem) as to_user
                                from 
                                    tweet_main_table t, base d,
                                    unnest(string_to_array(t.mentions, '||')) WITH ORDINALITY a(elem, nr)
                                where
                                    d.tweet_Tweet_id = t.tweet_Tweet_id
                                    and lower(elem) not in ({5})
                            ) ,
                            sums as (
                                select distinct from_user from base2 union select distinct to_user from base2
                            ),
                            ids as (
                                select from_user, count(*) node_size from sums group by from_user
                            ),
                            ids2 as (
                                select *, row_number() over (order by node_size desc) as id from ids
                            )
                            select 
                                a.from_user as from_name, id1.id as from,  id1.node_size as from_size, 
                                a.to_user as to_name,  id2.id as to,  id2.node_size as to_size,  
                                count(*) as value
                            from base2 a, ids2 id1, ids2 id2
                            where a.from_user = id1.from_user and a.to_user = id2.from_user
                            group by a.from_user, a.to_user, id1.id, id2.id, id1.node_size, id2.node_size 
                            order by count(*) desc
                            limit {4}

                        """.format(track, start_date, end_date, domain, str(100) if top_n == '' else str(top_n), excluded_terms),engine)
            else:
                temp = pd.read_sql_query("""
                            with 
                            base2 as (
                                select distinct
                                    t.tweet_Tweet_id, 
                                    username as from_user,
                                    lower(elem) as to_user
                                from 
                                    tweet_main_table t, tracker_tracker b,
                                    unnest(string_to_array(t.mentions, '||')) WITH ORDINALITY a(elem, nr)
                                where
                                    b.id in ({0}) and date(tweet_created_at) between '{1}' and '{2}'
                                    and lower(elem) not in ({4})  and b.query_name = t.query_name 
                            ) ,
                            sums as (
                                select distinct from_user from base2 union select distinct to_user from base2
                            ),
                            ids as (
                                select from_user, count(*) node_size from sums group by from_user
                            ),
                            ids2 as (
                                select *, row_number() over (order by node_size desc) as id from ids
                            )
                            select 
                                a.from_user as from_name, id1.id as from,  id1.node_size as from_size, 
                                a.to_user as to_name,  id2.id as to,  id2.node_size as to_size,  
                                count(*) as value
                            from base2 a, ids2 id1, ids2 id2
                            where a.from_user = id1.from_user and a.to_user = id2.from_user
                            group by a.from_user, a.to_user, id1.id, id2.id, id1.node_size, id2.node_size 
                            order by count(*) desc
                            limit {3}
                        """.format(track, start_date, end_date, str(100) if top_n == '' else str(top_n), excluded_terms ),engine)

    
            tmp1 = temp[['from', 'from_name']]
            tmp2 = temp[['to', 'to_name']]
            tmp1.columns =['id', 'label']
            tmp2.columns =['id', 'label']
            distinct = pd.concat([tmp1, tmp2], axis=0)
            distinct.drop_duplicates(inplace=True)
            distinct['value'] = 1
           
            print(distinct, temp)
            
            G_symmetric = nx.Graph() 
            for index, row in temp.iterrows():
                G_symmetric.add_edge(row['from_name'], row['to_name'])
            
            degree_centrality = nx.degree_centrality(G_symmetric)
            betweenness_centrality = nx.betweenness_centrality(G_symmetric)
            eigen_centrality = nx.eigenvector_centrality(G_symmetric, max_iter=500)
            clustering = nx.clustering(G_symmetric)
            
            xx = dict(sorted(degree_centrality.items(), key=lambda item: item[1])) 
            yy = dict(sorted(betweenness_centrality.items(), key=lambda item: item[1])) 
            ie = dict(sorted(eigen_centrality.items(), key=lambda item: item[1])) 
            cl = dict(sorted(clustering.items(), key=lambda item: item[1])) 
            
            aa = []
            bb = []
            cc = []
            dd = []

            for i, v in enumerate(xx.keys()):
                aa.append([v,xx[v]])
    
            for i, v in enumerate(yy.keys()):
                bb.append([v,yy[v]])

            for i, v in enumerate(ie.keys()):
                cc.append([v,ie[v]])

            for i, v in enumerate(cl.keys()):
                dd.append([v,cl[v]])
            
            degree_df = pd.DataFrame(aa, columns=['label','value'])
            bet_df = pd.DataFrame(bb, columns=['label','value'])
            eigen = pd.DataFrame(cc, columns=['label','value'])
            clustering = pd.DataFrame(dd, columns=['label','value'])
            engine.dispose()
            return JsonResponse({'data': temp[['from', 'to', 'value']].to_dict(orient='records'), 'data2': distinct.to_dict(orient='records'),
                                                'degree_df': degree_df.to_json(orient='records'),
                                                'bet_df': bet_df.to_json(orient='records'),
                                                'ieg_df': eigen.to_json(orient='records'),
                                                'clus_df': clustering.to_json(orient='records')})
        elif node_level == 'mention_cooccurrence':
            if domain == '':
                temp = pd.read_sql_query("""
                        with 
                        base as (
                            select distinct
                                t.tweet_Tweet_id, lower(elem) as tag
                            from 
                                tweet_main_table t, tracker_tracker b, 
                                unnest(string_to_array(t.mentions, '||')) WITH ORDINALITY a(elem, nr)
                            where
                                b.id in ({0}) and b.query_name = t.query_name and date(t.tweet_created_at) between '{1}' and '{2}'
                                and lower(elem) not in ({4})
                        ),
                        ids as (
                            select tag, count(*) node_size from base group by tag
                        ),
                        ids2 as (
                            select *, row_number() over (order by node_size desc) as id from ids
                        )
                        select 
                            a.tag as from_name, id1.id as from,  id1.node_size as from_size, 
                            b.tag as to_name,  id2.id as to,  id2.node_size as to_size,  
                            count(*) as value
                        from base a, base b, ids2 id1, ids2 id2
                        where a.tweet_Tweet_id=b.tweet_Tweet_id and a.tag < b.tag and a.tag = id1.tag and b.tag=id2.tag
                        group by a.tag, b.tag, id1.id, id2.id, id1.node_size, id2.node_size 
                        order by count(*) desc
                        limit {3}
                        """.format(track, start_date, end_date, str(100) if top_n == '' else str(top_n) , excluded_terms),engine)
            else:
                temp = pd.read_sql_query("""
                        with 
                        domains as (
                            select domain_id, max(domain_name) as domain_name from df_annotation_domain group by domain_id
                        ),
                        base as (
                            select distinct
                                t.tweet_Tweet_id
                            from 
                                tweet_main_table t, tracker_tracker b, domains d,
                                unnest(string_to_array(t.domain_entities, '||')) WITH ORDINALITY a(elem, nr)
                            where
                                b.id in ({0}) and b.query_name = t.query_name 
                                and split_part(elem, '=', 1) = lower(d.domain_name)
                                and d.domain_id::bigint in ({3})
                                and date(t.tweet_created_at) between '{1}' and '{2}'
                        ),
                        base2 as (
                            select distinct
                                t.tweet_Tweet_id, 
                                lower(elem) as tag
                            from 
                                tweet_main_table t, base d,
                                unnest(string_to_array(t.mentions, '||')) WITH ORDINALITY a(elem, nr)
                            where
                                d.tweet_Tweet_id = t.tweet_Tweet_id
                                and lower(elem) not in ({5})
                        ),
                        ids as (
                            select tag, count(*) node_size from base2 group by tag
                        ),
                        ids2 as (
                            select *, row_number() over (order by node_size desc) as id from ids
                        )
                        select 
                            a.tag as from_name, id1.id as from,  id1.node_size as from_size, 
                            b.tag as to_name,  id2.id as to,  id2.node_size as to_size,  
                            count(*) as value
                        from base2 a, base2 b, ids2 id1, ids2 id2
                        where a.tweet_Tweet_id=b.tweet_Tweet_id and a.tag < b.tag and a.tag = id1.tag and b.tag = id2.tag
                        group by a.tag, b.tag, id1.id, id2.id, id1.node_size, id2.node_size 
                        order by count(*) desc
                        limit {4}
                        """.format(track, start_date, end_date, domain, str(100) if top_n == '' else str(top_n), excluded_terms ),engine)

            tmp1 = temp[['from', 'from_name']]
            tmp2 = temp[['to', 'to_name']]
            tmp1.columns =['id', 'label']
            tmp2.columns =['id', 'label']
            distinct = pd.concat([tmp1, tmp2], axis=0)
            distinct.drop_duplicates(inplace=True)
            distinct['value'] = 1
        
            print(distinct, temp)
            
            G_symmetric = nx.Graph() 
            for index, row in temp.iterrows():
                G_symmetric.add_edge(row['from_name'], row['to_name'])
            
            degree_centrality = nx.degree_centrality(G_symmetric)
            betweenness_centrality = nx.betweenness_centrality(G_symmetric)
            eigen_centrality = nx.eigenvector_centrality(G_symmetric, max_iter=500)
            clustering = nx.clustering(G_symmetric)
            
            xx = dict(sorted(degree_centrality.items(), key=lambda item: item[1])) 
            yy = dict(sorted(betweenness_centrality.items(), key=lambda item: item[1])) 
            ie = dict(sorted(eigen_centrality.items(), key=lambda item: item[1])) 
            cl = dict(sorted(clustering.items(), key=lambda item: item[1])) 
            
            aa = []
            bb = []
            cc = []
            dd = []

            for i, v in enumerate(xx.keys()):
                aa.append([v,xx[v]])
    
            for i, v in enumerate(yy.keys()):
                bb.append([v,yy[v]])

            for i, v in enumerate(ie.keys()):
                cc.append([v,ie[v]])

            for i, v in enumerate(cl.keys()):
                dd.append([v,cl[v]])
            
            degree_df = pd.DataFrame(aa, columns=['label','value'])
            bet_df = pd.DataFrame(bb, columns=['label','value'])
            eigen = pd.DataFrame(cc, columns=['label','value'])
            clustering = pd.DataFrame(dd, columns=['label','value'])
            engine.dispose()
            return JsonResponse({'data': temp[['from', 'to', 'value']].to_dict(orient='records'), 'data2': distinct.to_dict(orient='records'),
                                                'degree_df': degree_df.to_json(orient='records'),
                                                'bet_df': bet_df.to_json(orient='records'),
                                                'ieg_df': eigen.to_json(orient='records'),
                                                'clus_df': clustering.to_json(orient='records')})

        elif node_level == 'bigram':
            if domain == '':
                print('***------------------------------------------------------- BIGRAM:', processor, start_date, end_date, str(100) if top_n == '' else str(top_n))
                temp = pd.read_sql_query("""
                with 
                    base as (
                        SELECT t.tweet_Tweet_id, elem, nr
                        FROM   df_tweets_processed t, analyzer_processor_nlp b,
                        unnest(string_to_array(t.tweet_text, ' ')) WITH ORDINALITY a(elem, nr)
                        where 
                            b.id in ({0})
                            and t.processor_name = b.name
                            and date(t.created_at) between '{1}' and '{2}'
                    ),
                    base2 as (
                        select distinct a.tweet_tweet_id, concat(a.elem,' ', b.elem) as bigram,a.elem el1, b.elem el2
                        from base a, base b
                        where a.tweet_tweet_id = b.tweet_tweet_id and a.nr + 1 = b.nr 
                        and a.elem <> '' and b.elem <> ''
                        and concat(a.elem,' ', b.elem) not in ({4})
                    ),
                    values as (select bigram, count(*) node_size from base2 group by bigram),
                    ids as (select bigram, row_number() over (order by node_size desc) id from values),
                    calcs as (
                        select a.bigram as from_name, b.bigram as to_name, count(*) as value
                        from base2 a, base2 b
                        where a.tweet_tweet_id = b.tweet_tweet_id and a.bigram < b.bigram
                        and a.el1 <> b.el1 and a.el1 <> b.el2 and a.el2 <> b.el1 and a.el2 <> b.el2
                        group by a.bigram, b.bigram
                        order by count(*) desc
                        limit {3}
                    )
                    select from_name, to_name, value, v1.node_size as from_size, v2.node_size as to_size, i1.id as from, i2.id as to
                    from calcs, values as v1, values as v2, ids as i1, ids as i2
                    where calcs.from_name = v1.bigram and calcs.to_name = v2.bigram and calcs.from_name = i1.bigram and calcs.to_name = i2.bigram 
                    
                """.format(processor, start_date, end_date, str(100) if top_n == '' else str(top_n), excluded_terms ), engine)
            else:
                temp = pd.read_sql_query("""
                    with domains as (
                        select domain_id, max(lower(domain_name)) as domain_name from df_annotation_domain group by domain_id
                    ),
                    base as (
                        SELECT distinct t.tweet_Tweet_id
                        FROM   df_tweets_processed t, analyzer_processor_nlp b, domains c, tweet_main_table d,
                        unnest(string_to_array(d.domain_entities, ' || ')) WITH ORDINALITY a(elem, nr)
                        where 
                            split_part(elem, '=', 1) = c.domain_name
                            and b.id in ({0})
                            and c.domain_id::int in ({3})
                            and t.processor_name = b.name
                            and t.tweet_tweet_id = d.tweet_tweet_id
                            and date(d.tweet_created_at) between '{1}' and '{2}'
                    ),
                    base_new as (
                        SELECT t.tweet_Tweet_id, elem, nr
                        FROM   df_tweets_processed t, base b,
                        unnest(string_to_array(t.tweet_text, ' ')) WITH ORDINALITY a(elem, nr)
                        where t.tweet_Tweet_id = b.tweet_Tweet_id
                    ),
                    base2 as (
                        select distinct a.tweet_tweet_id, concat(a.elem,' ', b.elem) as bigram,a.elem el1, b.elem el2
                        from base_new a, base_new b
                        where a.tweet_tweet_id = b.tweet_tweet_id and a.nr + 1 = b.nr 
                        and a.elem <> '' and b.elem <> ''
                        and concat(a.elem,' ', b.elem) not in ({5})
                    ),
                    values as (select bigram, count(*) node_size from base2 group by bigram),
                    ids as (select bigram, row_number() over (order by node_size desc) id from values),
                    calcs as (
                        select a.bigram as from_name, b.bigram as to_name, count(*) as value
                        from base2 a, base2 b
                        where a.tweet_tweet_id = b.tweet_tweet_id and a.bigram < b.bigram
                        and a.el1 <> b.el1 and a.el1 <> b.el2 and a.el2 <> b.el1 and a.el2 <> b.el2
                        group by a.bigram, b.bigram
                        order by count(*) desc
                        limit {4}
                    )
                    select from_name, to_name, value, v1.node_size as from_size, v2.node_size as to_size, i1.id as from, i2.id as to
                    from calcs, values as v1, values as v2, ids as i1, ids as i2
                    where calcs.from_name = v1.bigram and calcs.to_name = v2.bigram and calcs.from_name = i1.bigram and calcs.to_name = i2.bigram 

                """.format(processor, start_date, end_date, domain, str(100) if top_n == '' else str(top_n), excluded_terms), engine)
            distinct, degree_df, bet_df, eigen, clustering = get_network_metrics(temp)
            engine.dispose()
            return JsonResponse({'data': temp[['from', 'to', 'value']].to_dict(orient='records'), 'data2': distinct.to_dict(orient='records'),
                                                'degree_df': degree_df.to_json(orient='records'),
                                                'bet_df': bet_df.to_json(orient='records'),
                                                'ieg_df': eigen.to_json(orient='records'),
                                                'clus_df': clustering.to_json(orient='records')})
        
        elif node_level == 'retweet':
            if domain == '':
                print('***------------------------------------------------------- retweet:', processor, start_date, end_date, str(100) if top_n == '' else str(top_n))
                temp = pd.read_sql_query("""
                            with 
                            base2 as (
                                select distinct
                                    t.tweet_Tweet_id, 
                                    username as from_user,
                                    lower(retweeted_user) as to_user
                                from 
                                    tweet_main_table t, tracker_tracker b
                                where
                                    b.id in ({0}) and date(tweet_created_at) between '{1}' and '{2}'
                                    and (lower(retweeted_user) not in ({4}) and lower(username) not in ({4}) ) 
                                    and b.query_name = t.query_name and retweeted_user is not null
                            ) ,
                            base3 as (
                                select lower(a.to_user) as from_user, lower(b.to_user) as to_user
                                from base2 a, base2 b
                                where a.from_user = b.from_user and lower(a.to_user) < lower(b.to_user)
                            ),
                            sums as (
                                select from_user from base3 union all select to_user from base3
                            ),
                            ids as (
                                select from_user, count(*) node_size from sums group by from_user
                            ),
                            ids2 as (
                                select *, row_number() over (order by node_size desc) as id from ids
                            )
                            select 
                                a.from_user as from_name, id1.id as from,  id1.node_size as from_size, 
                                a.to_user as to_name,  id2.id as to,  id2.node_size as to_size,  
                                count(*) as value
                            from base3 a, ids2 id1, ids2 id2
                            where a.from_user = id1.from_user and a.to_user = id2.from_user
                            group by a.from_user, a.to_user, id1.id, id2.id, id1.node_size, id2.node_size 
                            order by id2.node_size desc
                            limit {3}
                        """.format(track, start_date, end_date, str(100) if top_n == '' else str(top_n), excluded_terms ),engine)
            else:
                temp = pd.read_sql_query("""
                            with 
                            domains as (
                                select domain_id, max(domain_name) as domain_name from df_annotation_domain group by domain_id
                            ),
                            base as (
                                select distinct
                                    t.tweet_Tweet_id
                                from 
                                    tweet_main_table t, tracker_tracker b, domains d,
                                    unnest(string_to_array(t.domain_entities, '||')) WITH ORDINALITY a(elem, nr)
                                where
                                    b.id in ({0}) and b.query_name = t.query_name 
                                    and split_part(elem, '=', 1) = lower(d.domain_name)
                                    and d.domain_id::bigint in ({3})
                                    and date(tweet_created_at) between '{1}' and '{2}'
                                    
                            ),
                            base2 as (
                                select distinct
                                    t.tweet_Tweet_id, username as from_user,
                                    lower(retweeted_user) as to_user
                                from 
                                    tweet_main_table t, base d
                                where
                                    d.tweet_Tweet_id = t.tweet_Tweet_id
                                    and (lower(retweeted_user) not in ({5}) and lower(username) not in ({5}) ) 
                                    and retweeted_user is not null
                            ) ,
                            sums as (
                                select distinct from_user from base2 union select distinct to_user from base2
                            ),
                            ids as (
                                select from_user, count(*) node_size from sums group by from_user
                            ),
                            ids2 as (
                                select *, row_number() over (order by node_size desc) as id from ids
                            )
                            select 
                                a.from_user as from_name, id1.id as from,  id1.node_size as from_size, 
                                a.to_user as to_name,  id2.id as to,  id2.node_size as to_size,  
                                count(*) as value
                            from base2 a, ids2 id1, ids2 id2
                            where a.from_user = id1.from_user and a.to_user = id2.from_user
                            group by a.from_user, a.to_user, id1.id, id2.id, id1.node_size, id2.node_size 
                            order by count(*) desc
                            limit {4}

                        """.format(track, start_date, end_date, domain, str(100) if top_n == '' else str(top_n), excluded_terms),engine)
            distinct, degree_df, bet_df, eigen, clustering = get_network_metrics(temp)
            engine.dispose()
            return JsonResponse({'data': temp[['from', 'to', 'value']].to_dict(orient='records'), 'data2': distinct.to_dict(orient='records'),
                                                'degree_df': degree_df.to_json(orient='records'),
                                                'bet_df': bet_df.to_json(orient='records'),
                                                'ieg_df': eigen.to_json(orient='records'),
                                                'clus_df': clustering.to_json(orient='records')})
        
        elif node_level == 'quote':
            if domain == '':
                print('***------------------------------------------------------- retweet:', processor, start_date, end_date, str(100) if top_n == '' else str(top_n))
                temp = pd.read_sql_query("""
                            with 
                            base2 as (
                                select distinct
                                    t.tweet_Tweet_id, 
                                    username as from_user,
                                    lower(quoted_user) as to_user
                                from 
                                    tweet_main_table t, tracker_tracker b
                                where
                                    b.id in ({0}) and date(tweet_created_at) between '{1}' and '{2}'
                                    and (lower(quoted_user) not in ({4}) and lower(username) not in ({4}) ) 
                                    and b.query_name = t.query_name and quoted_user is not null
                            ) ,
                            sums as (
                                select distinct from_user from base2 union select distinct to_user from base2
                            ),
                            ids as (
                                select from_user, count(*) node_size from sums group by from_user
                            ),
                            ids2 as (
                                select *, row_number() over (order by node_size desc) as id from ids
                            )
                            select 
                                a.from_user as from_name, id1.id as from,  id1.node_size as from_size, 
                                a.to_user as to_name,  id2.id as to,  id2.node_size as to_size,  
                                count(*) as value
                            from base2 a, ids2 id1, ids2 id2
                            where a.from_user = id1.from_user and a.to_user = id2.from_user
                            group by a.from_user, a.to_user, id1.id, id2.id, id1.node_size, id2.node_size 
                            order by count(*) desc
                            limit {3}
                        """.format(track, start_date, end_date, str(100) if top_n == '' else str(top_n), excluded_terms ),engine)
            else:
                temp = pd.read_sql_query("""
                            with 
                            domains as (
                                select domain_id, max(domain_name) as domain_name from df_annotation_domain group by domain_id
                            ),
                            base as (
                                select distinct
                                    t.tweet_Tweet_id
                                from 
                                    tweet_main_table t, tracker_tracker b, domains d,
                                    unnest(string_to_array(t.domain_entities, '||')) WITH ORDINALITY a(elem, nr)
                                where
                                    b.id in ({0}) and b.query_name = t.query_name 
                                    and split_part(elem, '=', 1) = lower(d.domain_name)
                                    and d.domain_id::bigint in ({3})
                                    and date(tweet_created_at) between '{1}' and '{2}'
                                    
                            ),
                            base2 as (
                                select distinct
                                    t.tweet_Tweet_id, username as from_user,
                                    lower(quoted_user) as to_user
                                from 
                                    tweet_main_table t, base d
                                where
                                    d.tweet_Tweet_id = t.tweet_Tweet_id
                                    and (lower(quoted_user) not in ({5}) and lower(quoted_user) not in ({5}) ) 
                                    and quoted_user is not null
                            ) ,
                            sums as (
                                select distinct from_user from base2 union select distinct to_user from base2
                            ),
                            ids as (
                                select from_user, count(*) node_size from sums group by from_user
                            ),
                            ids2 as (
                                select *, row_number() over (order by node_size desc) as id from ids
                            )
                            select 
                                a.from_user as from_name, id1.id as from,  id1.node_size as from_size, 
                                a.to_user as to_name,  id2.id as to,  id2.node_size as to_size,  
                                count(*) as value
                            from base2 a, ids2 id1, ids2 id2
                            where a.from_user = id1.from_user and a.to_user = id2.from_user
                            group by a.from_user, a.to_user, id1.id, id2.id, id1.node_size, id2.node_size 
                            order by count(*) desc
                            limit {4}

                        """.format(track, start_date, end_date, domain, str(100) if top_n == '' else str(top_n), excluded_terms),engine)
            distinct, degree_df, bet_df, eigen, clustering = get_network_metrics(temp)
            engine.dispose()
            return JsonResponse({'data': temp[['from', 'to', 'value']].to_dict(orient='records'), 'data2': distinct.to_dict(orient='records'),
                                                'degree_df': degree_df.to_json(orient='records'),
                                                'bet_df': bet_df.to_json(orient='records'),
                                                'ieg_df': eigen.to_json(orient='records'),
                                                'clus_df': clustering.to_json(orient='records')})
        
        elif node_level == 'replied_to':
            if domain == '':
                print('***------------------------------------------------------- retweet:', processor, start_date, end_date, str(100) if top_n == '' else str(top_n))
                temp = pd.read_sql_query("""
                            with 
                            base2 as (
                                select distinct
                                    t.tweet_Tweet_id, 
                                    username as from_user,
                                    lower(replied_to_user) as to_user
                                from 
                                    tweet_main_table t, tracker_tracker b
                                where
                                    b.id in ({0}) and date(tweet_created_at) between '{1}' and '{2}'
                                    and (lower(replied_to_user) not in ({4}) and lower(username) not in ({4}) ) 
                                    and b.query_name = t.query_name and replied_to_user is not null
                            ) ,
                            sums as (
                                select distinct from_user from base2 union select distinct to_user from base2
                            ),
                            ids as (
                                select from_user, count(*) node_size from sums group by from_user
                            ),
                            ids2 as (
                                select *, row_number() over (order by node_size desc) as id from ids
                            )
                            select 
                                a.from_user as from_name, id1.id as from,  id1.node_size as from_size, 
                                a.to_user as to_name,  id2.id as to,  id2.node_size as to_size,  
                                count(*) as value
                            from base2 a, ids2 id1, ids2 id2
                            where a.from_user = id1.from_user and a.to_user = id2.from_user
                            group by a.from_user, a.to_user, id1.id, id2.id, id1.node_size, id2.node_size 
                            order by count(*) desc
                            limit {3}
                        """.format(track, start_date, end_date, str(100) if top_n == '' else str(top_n), excluded_terms ),engine)
            else:
                temp = pd.read_sql_query("""
                            with 
                            domains as (
                                select domain_id, max(domain_name) as domain_name from df_annotation_domain group by domain_id
                            ),
                            base as (
                                select distinct
                                    t.tweet_Tweet_id
                                from 
                                    tweet_main_table t, tracker_tracker b, domains d,
                                    unnest(string_to_array(t.domain_entities, '||')) WITH ORDINALITY a(elem, nr)
                                where
                                    b.id in ({0}) and b.query_name = t.query_name 
                                    and split_part(elem, '=', 1) = lower(d.domain_name)
                                    and d.domain_id::bigint in ({3})
                                    and date(tweet_created_at) between '{1}' and '{2}'
                                    
                            ),
                            base2 as (
                                select distinct
                                    t.tweet_Tweet_id, username as from_user,
                                    lower(replied_to_user) as to_user
                                from 
                                    tweet_main_table t, base d
                                where
                                    d.tweet_Tweet_id = t.tweet_Tweet_id
                                    and (lower(replied_to_user) not in ({5}) and lower(replied_to_user) not in ({5}) ) 
                                    and replied_to_user is not null
                            ) ,
                            sums as (
                                select distinct from_user from base2 union select distinct to_user from base2
                            ),
                            ids as (
                                select from_user, count(*) node_size from sums group by from_user
                            ),
                            ids2 as (
                                select *, row_number() over (order by node_size desc) as id from ids
                            )
                            select 
                                a.from_user as from_name, id1.id as from,  id1.node_size as from_size, 
                                a.to_user as to_name,  id2.id as to,  id2.node_size as to_size,  
                                count(*) as value
                            from base2 a, ids2 id1, ids2 id2
                            where a.from_user = id1.from_user and a.to_user = id2.from_user
                            group by a.from_user, a.to_user, id1.id, id2.id, id1.node_size, id2.node_size 
                            order by count(*) desc
                            limit {4}

                        """.format(track, start_date, end_date, domain, str(100) if top_n == '' else str(top_n), excluded_terms),engine)
            distinct, degree_df, bet_df, eigen, clustering = get_network_metrics(temp)
            engine.dispose()
            return JsonResponse({'data': temp[['from', 'to', 'value']].to_dict(orient='records'), 'data2': distinct.to_dict(orient='records'),
                                                'degree_df': degree_df.to_json(orient='records'),
                                                'bet_df': bet_df.to_json(orient='records'),
                                                'ieg_df': eigen.to_json(orient='records'),
                                                'clus_df': clustering.to_json(orient='records')})


    elif which == 'domain_top_entities_graph':
        engine = create_engine(db_connection_url)
        temp = pd.read_sql_query("""
                with base as (
                    select b.domain_name, c.entity_name, count(*) total, count(*) over (partition by domain_name) as domain_tot
                from 
                    df_annotations a, 
                    tracker_tracker t,
                    (select distinct lower(domain_name) as domain_name, domain_id, domain_desc from df_annotation_domain where domain_id::int in ({0})) b, 
                    (select distinct lower(entity_name) as entity_name, entity_id, entity_desc from df_annotation_entity) c
                where a.domain_id = b.domain_id and a.entity_id = c.entity_id and 
                    a.query_name = t.query_name and t.id in ({1})
                group by b.domain_name, c.entity_name 
                )
                select 
                    *, 
                    row_number() over (partition by domain_name order by total desc) as rc,
                    DENSE_RANK() over (order by domain_tot desc) as rc_domain
                from base
            """.format(request.POST.get('domain'), request.POST.get('track')), engine)
        arr = []
        temp = temp[(temp['rc_domain'] <= 10) & (temp['rc'] <= 20)]
        for domain in set(temp['domain_name']):
            the_dict = {}
            the_dict['name'] =domain
            the_dict['children'] = []
            entities = temp[temp['domain_name'] == domain]
            for index, row in entities.iterrows():
                the_dict['children'].append({ 'name': row['entity_name'], 'value': row['total'] })
            arr.append(the_dict)
        engine.dispose()
        return JsonResponse(arr, safe=False)
    elif which == 'get_comparisons_metrics':
        engine = create_engine(db_connection_url)
        source1 = request.POST.get('source1')
        source2 = request.POST.get('source2')
        start_date1 = request.POST.get('start_date1')
        start_date2 = request.POST.get('start_date2')
        end_date1 = request.POST.get('end_date1')
        end_date2 = request.POST.get('end_date2')
        level = request.POST.get('level')
        
        if level == 'mentions' or level == 'hashtags':
            print('OOOOOOOOOO')
            temp = pd.read_sql_query("""
                    with period1 as (
                        select 
                            lower(elem) as tag,
                            sum(polarity*multiplier) / sum(multiplier) as avg_polarity,
                            sum(subjectivity*multiplier) / sum(multiplier) as avg_subjectivity,
                            sum(multiplier) as total
                        from 
                            df_tweets_processed v, 
                            analyzer_processor_nlp b, 
                            tweet_main_table d,
                            unnest(string_to_array(d.{6}, '||')) WITH ORDINALITY a(elem, nr) 
                        where 
                            v.tweet_tweet_id = d.tweet_tweet_id and
                            ((b.id in ({0}) and date(v.created_at) between '{1}' and '{2}'))
                            and v.processor_name = b.name
                        group by
                            lower(elem)
                    ),
                    period2 as (
                        select 
                            lower(elem) as tag,
                            sum(polarity*multiplier) / sum(multiplier) as avg_polarity,
                            sum(subjectivity*multiplier) / sum(multiplier) as avg_subjectivity,
                            sum(multiplier) as total
                        from 
                            df_tweets_processed v, 
                            analyzer_processor_nlp b, 
                            tweet_main_table d,
                            unnest(string_to_array(d.{6}, '||')) WITH ORDINALITY a(elem, nr) 
                        where 
                            v.tweet_tweet_id = d.tweet_tweet_id and
                            ((b.id in ({3}) and date(v.created_at) between '{4}' and '{5}'))
                            and v.processor_name = b.name
                        group by
                            lower(elem)
                    ),
                    comp as (
                    select 
                        coalesce(a.tag, b.tag) as tag,
                        row_number() over (order by a.total desc nulls last) as rank_period1,
                        row_number() over (order by b.total desc nulls last) as rank_period2,
                        row_number() over (order by case when b.total is null then a.total end desc nulls last) as rank_period1_only,
                        row_number() over (order by case when a.total is null then b.total end desc nulls last) as rank_period2_only,
                        coalesce(a.total,0) as total_period1,
                        coalesce(b.total,0) as total_period2,
                        coalesce(a.avg_polarity,0) as polarity_avg_period1,
                        coalesce(b.avg_polarity,0) as polarity_avg_period2,
                        coalesce(a.avg_subjectivity,0) as subjectivity_avg_period1,
                        coalesce(b.avg_subjectivity,0) as subjectivity_avg_period2
                    from 
                        period1 a 
                        full join 
                        period2 b on a.tag = b.tag

                    )
                    select 
                        * 
                    from 
                        comp 
                    where 
                        rank_period1 <= 50 or rank_period2 <= 50  or rank_period1_only <= 50 or rank_period2_only <= 50
    
                    """.format(source1, start_date1, end_date1,source2, start_date2, end_date2, level), engine)
            return JsonResponse(temp.to_dict(orient='row'), safe=False)
        elif level == 'domains' or level == 'entities':
            temp = pd.read_sql_query("""
                with period1 as (
                        select 
                            lower(split_part(elem,'=',{7})) as tag,
                            sum(polarity*multiplier) / sum(multiplier) as avg_polarity,
                            sum(subjectivity*multiplier) / sum(multiplier) as avg_subjectivity,
                            sum(multiplier) as total
                        from 
                            df_tweets_processed v, 
                            analyzer_processor_nlp b, 
                            tweet_main_table d,
                            unnest(string_to_array(d.domain_entities, ' || ')) WITH ORDINALITY a(elem, nr) 
                        where 
                            v.tweet_tweet_id = d.tweet_tweet_id and
                            ((b.id in ({0}) and date(v.created_at) between '{1}' and '{2}'))
                            and v.processor_name = b.name
                        group by
                            lower(split_part(elem,'=',{7}))
                    ),
                    period2 as (
                        select 
                            lower(split_part(elem,'=',{7})) as tag,
                            sum(polarity*multiplier) / sum(multiplier) as avg_polarity,
                            sum(subjectivity*multiplier) / sum(multiplier) as avg_subjectivity,
                            sum(multiplier) as total
                        from 
                            df_tweets_processed v, 
                            analyzer_processor_nlp b, 
                            tweet_main_table d,
                            unnest(string_to_array(d.domain_entities, ' || ')) WITH ORDINALITY a(elem, nr) 
                        where 
                            v.tweet_tweet_id = d.tweet_tweet_id and
                            ((b.id in ({3}) and date(v.created_at) between '{4}' and '{5}'))
                            and v.processor_name = b.name
                        group by
                            lower(split_part(elem,'=',{7}))
                    ),
                    comp as (
                    select 
                        coalesce(a.tag, b.tag) as tag,
                        row_number() over (order by a.total desc nulls last) as rank_period1,
                        row_number() over (order by b.total desc nulls last) as rank_period2,
                        row_number() over (order by case when b.total is null then a.total end desc nulls last) as rank_period1_only,
                        row_number() over (order by case when a.total is null then b.total end desc nulls last) as rank_period2_only,
                        coalesce(a.total,0) as total_period1,
                        coalesce(b.total,0) as total_period2,
                        coalesce(a.avg_polarity,0) as polarity_avg_period1,
                        coalesce(b.avg_polarity,0) as polarity_avg_period2,
                        coalesce(a.avg_subjectivity,0) as subjectivity_avg_period1,
                        coalesce(b.avg_subjectivity,0) as subjectivity_avg_period2
                    from 
                        period1 a 
                        full join 
                        period2 b on a.tag = b.tag

                    )
                    select 
                        * 
                    from 
                        comp 
                    where 
                        rank_period1 <= 50 or rank_period2 <= 50  or rank_period1_only <= 50 or rank_period2_only <= 50
                    """.format(source1, start_date1, end_date1,source2, start_date2, end_date2, level, '1' if level =='domains' else '2'), engine)
        elif level in ('retweeted_user', 'quoted_user','replied_to_user'):
            metric = ''
            if level == 'retweeted_user':
                metric = 'tweet_retweet_count'
            elif level == 'quoted_user':
                metric = 'tweet_quote_count'
            else:
                metric = 'tweet_reply_count'

            temp = pd.read_sql_query("""
                with period1 as (
                        select distinct
                            lower({6}) as tag,
                            avg(polarity) as avg_polarity,
                            avg(subjectivity) as avg_subjectivity,
                            max({7}) as total
                        from 
                            df_tweets_processed v, 
                            analyzer_processor_nlp b,
                            tweet_main_table d
                        where 
                            v.tweet_tweet_id = d.{8} and
                            ((b.id in ({0}) and date(v.created_at) between '{1}' and '{2}'))
                            and v.processor_name = b.name
                            and {6} is not null
                        group by
                            lower({6}) 
                    
                    ),
                    period2 as (
                        select distinct
                            lower({6}) as tag,
                            avg(polarity) as avg_polarity,
                            avg(subjectivity) as avg_subjectivity,
                            max({7}) as total
                        from 
                            tweet_main_table d,
                            df_tweets_processed v, 
                            analyzer_processor_nlp b 
                        where 
                            v.tweet_tweet_id = d.{8} and
                            ((b.id in ({3}) and date(v.created_at) between '{4}' and '{5}'))
                            and v.processor_name = b.name
                            and {6} is not null
                        group by
                            lower({6}) 
                    ),
                    comp as (
                    select 
                        coalesce(a.tag, b.tag) as tag,
                        row_number() over (order by a.total desc nulls last) as rank_period1,
                        row_number() over (order by b.total desc nulls last) as rank_period2,
                        row_number() over (order by case when b.total is null then a.total end desc nulls last) as rank_period1_only,
                        row_number() over (order by case when a.total is null then b.total end desc nulls last) as rank_period2_only,
                        coalesce(a.total,0) as total_period1,
                        coalesce(b.total,0) as total_period2,
                        coalesce(a.avg_polarity,0) as polarity_avg_period1,
                        coalesce(b.avg_polarity,0) as polarity_avg_period2,
                        coalesce(a.avg_subjectivity,0) as subjectivity_avg_period1,
                        coalesce(b.avg_subjectivity,0) as subjectivity_avg_period2
                    from 
                        period1 a 
                        full join 
                        period2 b on a.tag = b.tag

                    )
                    select 
                        * 
                    from 
                        comp 
                    where 
                        rank_period1 <= 50 or rank_period2 <= 50  or rank_period1_only <= 50 or rank_period2_only <= 50
                    """.format(source1, start_date1, end_date1,source2, start_date2, end_date2, level,metric, 'retweeted_tweet_id' if level == 'retweeted_user' else 'tweet_tweet_id'), engine)
            print('quoted...')
        elif level in ['annotation_persons','annotation_org','annotation_product','annotation_place','annotation_other']:
            temp = pd.read_sql_query("""
                with period1 as (
                        select 
                            lower(elem) as tag,
                            sum(polarity*multiplier) / sum(multiplier) as avg_polarity,
                            sum(subjectivity*multiplier) / sum(multiplier) as avg_subjectivity,
                            sum(multiplier) as total
                        from 
                            df_tweets_processed v, 
                            analyzer_processor_nlp b, 
                            tweet_main_table d,
                            unnest(string_to_array(d.{6}, '||')) WITH ORDINALITY a(elem, nr) 
                        where 
                            v.tweet_tweet_id = d.tweet_tweet_id and
                            ((b.id in ({0}) and date(v.created_at) between '{1}' and '{2}'))
                            and v.processor_name = b.name
                        group by
                            lower(elem)
                    ),
                    period2 as (
                        select 
                            lower(elem) as tag,
                            sum(polarity*multiplier) / sum(multiplier) as avg_polarity,
                            sum(subjectivity*multiplier) / sum(multiplier) as avg_subjectivity,
                            sum(multiplier) as total
                        from 
                            tweet_main_table d,
                            df_tweets_processed v, 
                            analyzer_processor_nlp b ,
                            unnest(string_to_array(d.{6}, '||')) WITH ORDINALITY a(elem, nr) 
                        where 
                            v.tweet_tweet_id = d.tweet_tweet_id and
                            ((b.id in ({3}) and date(v.created_at) between '{4}' and '{5}'))
                            and v.processor_name = b.name
                        group by
                            lower(elem)
                    ),
                    comp as (
                    select 
                        coalesce(a.tag, b.tag) as tag,
                        row_number() over (order by a.total desc nulls last) as rank_period1,
                        row_number() over (order by b.total desc nulls last) as rank_period2,
                        row_number() over (order by case when b.total is null then a.total end desc nulls last) as rank_period1_only,
                        row_number() over (order by case when a.total is null then b.total end desc nulls last) as rank_period2_only,
                        coalesce(a.total,0) as total_period1,
                        coalesce(b.total,0) as total_period2,
                        coalesce(a.avg_polarity,0) as polarity_avg_period1,
                        coalesce(b.avg_polarity,0) as polarity_avg_period2,
                        coalesce(a.avg_subjectivity,0) as subjectivity_avg_period1,
                        coalesce(b.avg_subjectivity,0) as subjectivity_avg_period2
                    from 
                        period1 a 
                        full join 
                        period2 b on a.tag = b.tag

                    )
                    select 
                        * 
                    from 
                        comp 
                    where 
                        rank_period1 <= 50 or rank_period2 <= 50  or rank_period1_only <= 50 or rank_period2_only <= 50
                    """.format(source1, start_date1, end_date1,source2, start_date2, end_date2, level), engine)
        elif level == 'word':
            temp = pd.read_sql_query("""
     
                    (SELECT 'period1' as period, elem as tag,count(distinct tweet_Tweet_id) as count
                    FROM   df_tweets_processed t, analyzer_processor_nlp b,
                    unnest(string_to_array(t.tweet_text, ' ')) WITH ORDINALITY a(elem, nr)  
                    where t.processor_name = b.name and elem > '' and b.id in ({0}) and date(created_at) between '{1}' and '{2}'
                    group by elem
                    order by count(distinct tweet_Tweet_id) desc
                    limit 250)
                    union all
                    (SELECT 'period2' as period, elem as tag,count(distinct tweet_Tweet_id) as count
                    FROM   df_tweets_processed t, analyzer_processor_nlp b,
                    unnest(string_to_array(t.tweet_text, ' ')) WITH ORDINALITY a(elem, nr)  
                    where t.processor_name = b.name and elem > '' and b.id in ({3}) and date(created_at) between '{4}' and '{5}'
                    group by elem
                    order by count(distinct tweet_Tweet_id) desc
                    limit 250)
                """.format(source1, start_date1, end_date1,source2, start_date2, end_date2), engine)
        engine.dispose()
 
        return JsonResponse(temp.to_dict(orient='row'), safe=False)
        
    
    elif which == 'cancel_processor':
        processors = request.POST.get('selected')
        delete = request.POST.get('delete')
        engine = create_engine(db_connection_url)
        temp_all = pd.read_sql_query("""
            select 
                a.id, a.name, 
                b.id as schedule_id, concat(a.name,'(id=',a.id::varchar(255),')') as processor_name, coalesce(repeats,0) as repeat, a.user_id
            from analyzer_processor_nlp a
            left join django_q_schedule b on position(concat('''',a.name,'''') in b.kwargs) > 0  and b.func = 'analyzer.nlp_processor.Processor' 
            where a.id in ({0}) 
            """.format(processors), engine)
        print(temp_all, processors)

        successes = ''
        message = ''
        message_deleted = ''
        to_delete_id = ''
        to_delete_name = ''

        for index, row in temp_all.iterrows():
            if(row['user_id'] != request.user.id):
                message = message + '\n ' + row['processor_name'] + ': You are not the owner of this processor.'.format(request.user)
            elif(row['repeat'] == 0):
                message = message + '\n' + row['processor_name'] + ': This task is already cancelled.'
                if delete == 'yes':
                    message_deleted = message_deleted + '\n' + row['processor_name'] + ': Successfully deleted.'
                    to_delete_id = to_delete_id + str(row['id']) +','
                    to_delete_name = to_delete_name + str(row['name']) +','
            else:
                message = message + '\n' + row['processor_name'] + ': Successfully cancelled.'
                successes = successes + str(row['schedule_id']) +','
                if delete == 'yes':
                    message_deleted = message_deleted + '\n' + row['processor_name'] + ': Successfully deleted.'
                    to_delete_id = to_delete_id + str(row['id']) +','
                    to_delete_name = to_delete_name + str(row['name']) +','
            
        conn = engine.connect()
        if(successes):
            print('DELETING processor schedule: ', successes[:-1])
            #conn.execute("DELETE from django_q_schedule where id in ({0})".format(successes[:-1]))
            #conn.close()
        
        if(to_delete_id):
            try:
                print('DELETING processor and its data: ', to_delete_id + ':::'+to_delete_name)
                #conn.execute("DELETE from analyzer_processor_nlp where id in ({0})".format(to_delete_id))
                #conn.execute("DELETE from df_tweets_processed where processor_name in ({0})".format(to_delete_name))
                #conn.close()
                #return JsonResponse({'result':'Successfully cancelled.'})
            except Exception as e:
                #conn.close()
                return JsonResponse({'result':'Unsuccessful. Please contact admin about this issue.' })
        
        engine.dispose()

        return JsonResponse({'result': message + '\n' + message_deleted})





        
    
    elif which == 'get_sentiments_and_tweets':
        engine = create_engine(db_connection_url)

        source = request.POST.get('source1')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        domain = request.POST.get('domain')
        entity = request.POST.get('entity')
        hashtag = request.POST.get('hashtag')
        user = request.POST.get('user')
        mention = request.POST.get('mention')
        phrase = request.POST.get('phrase')
        bucket_size = request.POST.get('bucket_size')

        criteria = ''
        domain = ' OR '.join("position('"+a+"'"+' in domain_entities)>0' for a in domain.split(',') if a!='')

        criteria += ' and (' + domain + ')' if domain else ''
        entity = ' OR '.join("position('"+a.lower()+"'"+' in lower(domain_entities))>0' for a in entity.split(',') if a!='')
        criteria += ' and (' + entity + ')' if entity else ''
        hashtag = ' OR '.join("position('"+a.lower()+"'"+' in lower(hashtags))>0' for a in hashtag.split(',') if a!='')
        criteria += ' and (' + hashtag + ')' if hashtag else ''
        user = ' OR '.join("position('"+a.lower()+"'"+' in lower(username))>0' for a in user.split(',') if a!='')
        criteria += ' and (' + user + ')' if user else ''
        mention = ' OR '.join("position('"+a.lower()+"'"+' in lower(mentions))>0' for a in mention.split(',') if a!='')
        criteria += ' and (' + mention + ')' if mention else ''
        phrase = ' OR '.join("position('"+a.lower()+"'"+' in lower(a.tweet_text))>0' for a in phrase.split(',') if a!='')
        criteria += ' and (' + phrase + ')' if phrase else ''

     
        

        temp_dist = pd.read_sql_query("""
                    with base as (
                        select 
                            (((polarity*{4})::int)::float / {4}) as bucket
                        from 
                            df_tweets_processed a, tweet_main_table b
                        where 
                            a.tweet_tweet_id = b.tweet_tweet_id 
                            and a.processor_name in (select processor_name from analyzer_processor_nlp where id in ({0}) )
                            and date(a.created_at) between '{1}' and '{2}'
                            {3}
                    
                        union all

                        select 
                            (((polarity*{4})::int)::float / {4})  as bucket
                        from 
                            df_tweets_processed a, tweet_main_table b
                        where 
                            a.tweet_tweet_id = b.retweeted_tweet_id 
                            and a.processor_name in (select processor_name from analyzer_processor_nlp where id in ({0}) )
                            and date(a.created_at) between '{1}' and '{2}'
                            {3}
                        )   
                        select 
                            bucket, count(*) as total
                        from 
                            base
                        group by 
                            bucket
                        order by 
                            bucket
                    """.format(source, start_date, end_date, '' if not criteria else criteria, bucket_size),engine)
        
        temp_sample = pd.read_sql_query("""
                    (
                        select distinct
                        b.tweet_text as original_Tweet, a.tweet_text as processed_tweet, a.tweet_tweet_id, a.created_at, subjectivity, polarity, domain_entities, hashtags, username, mentions, pos, noun_phrases,
                        tweet_retweet_count, type
                    from 
                        df_tweets_processed a, tweet_main_table b
                    where 
                        (a.tweet_tweet_id = b.tweet_tweet_id) 
                        and a.processor_name in (select name from analyzer_processor_nlp where id in ({0}) )
                        and date(a.created_at) between '{1}' and '{2}'
                        {3}
                        limit 50
                    )
                    union all
                    (
                        select distinct
                        b.tweet_text as original_Tweet, a.tweet_text as processed_tweet, a.tweet_tweet_id, a.created_at, subjectivity, polarity, domain_entities, hashtags, username, mentions, pos, noun_phrases,
                        tweet_retweet_count, type
                    from 
                        df_tweets_processed a, tweet_main_table b
                    where 
                        (a.tweet_tweet_id = b.retweeted_tweet_id) 
                        and a.processor_name in (select name from analyzer_processor_nlp where id in ({0}) )
                        and date(a.created_at) between '{1}' and '{2}'
                        {3}
                        limit 50
                    )
                    """.format(source, start_date, end_date, '' if not criteria else criteria),engine)
        lst = []
        for index, row in temp_sample.iterrows():
            lst.append([row['original_tweet'], row['processed_tweet'],   row['tweet_tweet_id'],
                        row['created_at'], row['subjectivity'], row['polarity'], 
                        row['domain_entities'], row['hashtags'], row['username'],
                        row['mentions'],row['pos'],row['noun_phrases'],
                        row['tweet_retweet_count'], row['type']])
        
        engine.dispose()
        return JsonResponse({'dist': temp_dist.to_json(orient='records'), 'sample': lst})
    elif which == 'get_dashboard_info':
        print('dashboard info')
        conn = engine.connect()
        conn.execute("""drop table if exists temp1;
                                create table temp1 as 
                        with active as (
                            select query_name from tracker_tracker a, django_q_schedule b 
                            where
                                position(concat('''',a.query_name,'''') in b.kwargs) > 0 
                                and b.func = 'tracker.tweet_collector.TweetCollector'
                                and a.query_name in (select elem from dashboard_preferences where which = 'track' and user_id = {0})
                        ),
                        base as (
                            select 
                            a.query_name,
                            DATE_TRUNC('minute', key::timestamp) as key_formatted, 
                            key,
                            count(*) as total, 
                            sum(case when type='replied_to' then 1 else 0 end) as replied_to,
                            sum(case when type='retweeted' then 1 else 0 end) retweeted,
                            sum(case when type='quoted' then 1 else 0 end) quoted,
                            sum(case when type is null then 1 else 0 end) regular
                            from tweet_main_table a, active b
                            where a.query_name = b.query_name
                            group by key,key_formatted,a.query_name
                        ),
                        base2 as (
                            select *, row_number() over (order by key desc) as rc
                            from base
                        )
                        select *, case when rc <= 25 then 'next' else 'prev' end as period 
                        from base2 where rc <= 50
                        ;

                        drop table if exists temp2;

                        create table temp2 as
                        (
                        with base as (
                            select a.query_name, period, retweeted_user as object, retweeted_text,max(tweet_retweet_count) as retweet_cnt
                            from tweet_main_table a, temp1 b
                            where 
                                a.query_name = b.query_name
                                and a.key = b.key
                            group by a.query_name, period, retweeted_user, retweeted_text
                        ),
                        base2 as (
                            select *,row_number() over (partition by period order by retweet_cnt desc) rc 
                            from base
                        )
                        select *, 'retweet' as which from base2
                        where rc <= 20
                        )
                        union all
                        (
                        with base as (
                            select t.query_name, period, split_part(elem, '=',1) as domain, null, count(*) as total
                            from tweet_main_table t, temp1 b,
                            unnest(string_to_array(t.domain_entities, ' || ')) WITH ORDINALITY a(elem, nr)
                            where 
                                t.query_name = b.query_name
                                and t.key = b.key
                            group by t.query_name, period, split_part(elem, '=',1)
                        ),
                        base2 as (
                            select *,row_number() over (partition by period order by total desc) rc 
                            from base
                        )
                        select *, 'domain' as which from base2
                        where rc <= 20
                        )
                        union all

                        (
                        with base as (
                            select t.query_name, period, split_part(elem, '=',2) as domain, null, count(*) as total
                            from tweet_main_table t, temp1 b,
                            unnest(string_to_array(t.domain_entities, ' || ')) WITH ORDINALITY a(elem, nr)
                            where 
                                t.query_name = b.query_name
                                and t.key = b.key
                            group by t.query_name, period, split_part(elem, '=',2)
                        ),
                        base2 as (
                            select *,row_number() over (partition by period order by total desc) rc 
                            from base
                        )
                        select *, 'entity' as which from base2
                        where rc <= 20
                        )
                        union all

                        (
                        with base as (
                            select t.query_name, period, elem, null, count(*) as total
                            from tweet_main_table t, temp1 b,
                            unnest(string_to_array(t.hashtags, '||')) WITH ORDINALITY a(elem, nr)
                            where 
                                t.query_name = b.query_name
                                and t.key = b.key
                            group by t.query_name, period, elem
                        ),
                        base2 as (
                            select *,row_number() over (partition by period order by total desc) rc 
                            from base
                        )
                        select *, 'hashtag' as which from base2
                        where rc <= 20
                        )
                        union all
                        (
                        with base as (
                            select t.query_name, period, elem, null, count(*) as total
                            from tweet_main_table t, temp1 b,
                            unnest(string_to_array(t.mentions, '||')) WITH ORDINALITY a(elem, nr)
                            where 
                                t.query_name = b.query_name
                                and t.key = b.key
                            group by t.query_name, period, elem
                        ),
                        base2 as (
                            select *,row_number() over (partition by period order by total desc) rc 
                            from base
                        )
                        select *, 'mention' as which from base2
                        where rc <= 20
                        )
                        union all
                        (
                        with base as (
                            select t.query_name, period, elem, null, count(*) as total
                            from tweet_main_table t, temp1 b,
                            unnest(string_to_array(t.annotation_org, '||')) WITH ORDINALITY a(elem, nr)
                            where 
                                t.query_name = b.query_name
                                and t.key = b.key
                            group by t.query_name, period, elem
                        ),
                        base2 as (
                            select *,row_number() over (partition by period order by total desc) rc 
                            from base
                        )
                        select *, 'annotation_org' as which from base2
                        where rc <= 20
                        )
                        union all
                        (
                        with base as (
                            select t.query_name, period, elem, null, count(*) as total
                            from tweet_main_table t, temp1 b,
                            unnest(string_to_array(t.annotation_product, '||')) WITH ORDINALITY a(elem, nr)
                            where 
                                t.query_name = b.query_name
                                and t.key = b.key
                            group by t.query_name, period, elem
                        ),
                        base2 as (
                            select *,row_number() over (partition by period order by total desc) rc 
                            from base
                        )
                        select *, 'annotation_product' as which from base2
                        where rc <= 20
                        )
                        union all
                        (

                        with base as (
                            select t.query_name, period, elem, null, count(*) as total
                            from tweet_main_table t, temp1 b,
                            unnest(string_to_array(t.annotation_persons, '||')) WITH ORDINALITY a(elem, nr)
                            where 
                                t.query_name = b.query_name
                                and t.key = b.key
                            group by t.query_name, period, elem
                        ),
                        base2 as (
                            select *,row_number() over (partition by period order by total desc) rc 
                            from base
                        )
                        select *, 'annotation_persons' as which from base2
                        where rc <= 20
                        )
                        union all
                        (

                        with base as (
                            select t.query_name, period, elem, null, count(*) as total
                            from tweet_main_table t, temp1 b,
                            unnest(string_to_array(t.annotation_place, '||')) WITH ORDINALITY a(elem, nr)
                            where 
                                t.query_name = b.query_name
                                and t.key = b.key
                            group by t.query_name, period, elem
                        ),
                        base2 as (
                            select *,row_number() over (partition by period order by total desc) rc 
                            from base
                        )
                        select *, 'annotation_place' as which from base2
                        where rc <= 20
                        )
                        union all
                        (

                        with base as (
                            select t.query_name, period, elem, null, count(*) as total
                            from tweet_main_table t, temp1 b,
                            unnest(string_to_array(t.annotation_other, '||')) WITH ORDINALITY a(elem, nr)
                            where 
                                t.query_name = b.query_name
                                and t.key = b.key
                            group by t.query_name, period, elem
                        ),
                        base2 as (
                            select *,row_number() over (partition by period order by total desc) rc 
                            from base
                        )
                        select *, 'annotation_other' as which from base2
                        where rc <= 20
                            )
                            
                            
                            union all
                        (

                            select t.query_name, period, coalesce(type,'regular') as domain, null, count(*) as total, null as rc,
                            'tweet_pie' as which
                            from tweet_main_table t, temp1 b,
                            unnest(string_to_array(t.domain_entities, ' || ')) WITH ORDINALITY a(elem, nr)
                            where 
                                t.query_name = b.query_name
                                and t.key = b.key
                            group by t.query_name, period, domain

                        );
    
        """.format(int(request.user.id)))


        try:
            conn.execute("""drop table if exists temp3;
                            create table temp3 as 
                            select 
                                period,
                                case when polarity <= -0.8 then '6 - Very Negative'
                                when polarity <= -0.5 then '5 - Negative'
                                when polarity < 0 then '4 - Slightly Negative'
                                when polarity = 0 then '3 - Neutral'
                                when polarity < 0.5 then '2 - Slightly Positive'
                                else '1 - Very Positive' end as severity, count(*) as total
                            from df_tweets_processed a,  temp1 b, tweet_main_table c
                            where a.query_name = b.query_name and a.tweet_tweet_id = c.tweet_tweet_id
                                    and b.key = c.key
                                    and a.processor_name in (select elem from dashboard_preferences where which = 'processor' and user_id = {0})
                            group by period, severity """.format(int(request.user.id)))
            polarity = pd.read_sql_query("""select * from temp3""", engine)
        except:
            polarity = pd.DataFrame()




        conn.close()

        

        temp_data = pd.read_sql_query("""select * from temp1""", engine)
        temp_sample = pd.read_sql_query("""select * from temp2 where rc <= 20""", engine)
        tweet_pie_prev = pd.read_sql_query("""select * from temp2 where which = 'tweet_pie' and period = 'prev'""", engine)
        tweet_pie_next = pd.read_sql_query("""select * from temp2 where which = 'tweet_pie' and period = 'next'""", engine)
       
 
        df = temp_sample.pivot_table('retweet_cnt', ['query_name', 'which', 'object'], 'period')

        df.reset_index( drop=False, inplace=True )
        df = df.reindex(['query_name', 'which', 'object' , 'retweeted_text', 'prev','next'], axis=1)
        df = df.fillna(0)
        df = df.sort_values(['which','next'],ascending=False)
        print(df)
        return JsonResponse({'retweet':df[df['which'] == 'retweet'].to_dict(orient='records'),
                             'mention':df[df['which'] == 'mention'].to_dict(orient='records'),
                             'hashtag':df[df['which'] == 'hashtag'].to_dict(orient='records'),
                             'entity':df[df['which'] == 'entity'].to_dict(orient='records'),
                             'domain':df[df['which'] == 'domain'].to_dict(orient='records'),
                             'annotation_product':df[df['which'] == 'annotation_product'].to_dict(orient='records'),
                             'annotation_place':df[df['which'] == 'annotation_place'].to_dict(orient='records'),
                             'annotation_persons':df[df['which'] == 'annotation_persons'].to_dict(orient='records'),
                             'annotation_other':df[df['which'] == 'annotation_other'].to_dict(orient='records'),
                             'annotation_org':df[df['which'] == 'annotation_org'].to_dict(orient='records'),
                             'trend': temp_data.to_dict(orient='records'),
                             'tweet_pie_prev': tweet_pie_prev.to_dict(orient='records'),
                             'tweet_pie_next': tweet_pie_next.to_dict(orient='records'),
                             'polarity': polarity.to_dict(orient='records')
                             })

    elif which == 'perform_summarizer':
        import uuid
        temp_table_name = 'tmp_' + uuid.uuid4().hex
        print('temporary table name: ', temp_table_name)
        engine = create_engine(db_connection_url)
        source = request.POST.get('source')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        domain = request.POST.get('domain')
        entity = request.POST.get('entity')
        hashtag = request.POST.get('hashtag')
        user = request.POST.get('user')
        mention = request.POST.get('mention')
        phrase = request.POST.get('phrase')
        bucket_size = request.POST.get('bucket_size')

        conn = engine.connect()
        try:
            conn.execute("""drop table if exists {3};
                            create table {3} as
                            select distinct a.tweet_tweet_id
                            from tweet_main_table a, df_tweets_processed b, analyzer_processor_nlp c
                            where 
                                a.tweet_tweet_id = b.tweet_tweet_id 
                                and c.name = b.processor_name
                                and c.id in ({0})
                                and date(a.tweet_created_at) between '{1}' and '{2}'
                        """.format(source, start_date, end_date, temp_table_name))


            severity = pd.read_sql_query("""
                    select 
                    ((coalesce(polarity,0)*10)::int) /10::float as severity, count(*) as total
                    FROM   df_tweets_processed t, {0} b 
                    where t.tweet_tweet_id = b.tweet_tweet_id 
                    group by severity
                    order by severity
                    """.format(temp_table_name), engine)
            subjectivity = pd.read_sql_query("""
                    select 
                    ((coalesce(subjectivity,0)*20)::int) /20::float as severity, count(*) as total
                    FROM   df_tweets_processed t, {0} b 
                    where t.tweet_tweet_id = b.tweet_tweet_id 
                    group by severity
                    order by severity
                    """.format(temp_table_name), engine)

            tweet_type = pd.read_sql_query("""
                    select coalesce(type,'regular') as domain, count(*) as total
                    from tweet_main_table t, {0} b
                    where 
                        t.tweet_tweet_id = b.tweet_tweet_id
                    group by domain
                    """.format(temp_table_name), engine)

            domains = pd.read_sql_query("""
                    select split_part(elem,'=',1) as domain, count(*) as total
                    from tweet_main_table t, {0} b,
                    unnest(string_to_array(t.domain_entities, ' || ')) WITH ORDINALITY a(elem, nr)
                    where 
                        t.tweet_tweet_id = b.tweet_tweet_id
                    group by domain
                    order by count(*) desc
                    """.format(temp_table_name), engine)
            domain_polarity = pd.read_sql_query("""
                    select 
                    split_part(elem,'=',1) as domain, 
                    case when polarity <= -0.8 then 'very_negative'
                    when polarity <= -0.5 then 'negative'
                    when polarity < 0 then 'slightly_negative'
                    when polarity = 0 then 'neutral'
                    when polarity < 0.5 then 'slightly_positive'
                    when polarity < 0.8 then 'positive'
                    else 'very_positive' end as severity, 
                    100 * (sum(case when polarity < 0 then -1 else 1 end)/sum(count(*)) over (partition by split_part(elem,'=',1))) as percent
                    from tweet_main_table t, df_tweets_processed b, {0} c,
                    unnest(string_to_array(t.domain_entities, ' || ')) WITH ORDINALITY a(elem, nr)
                    where 
                    t.tweet_tweet_id = b.tweet_tweet_id and b.tweet_tweet_id = c.tweet_tweet_id
                    group by domain, severity
                    order by domain, count(*) desc
                    """.format(temp_table_name),engine)
            
            domain_polarity = domain_polarity.pivot_table('percent', ['domain'], 'severity')
            domain_polarity.reset_index( drop=False, inplace=True )
            domain_polarity = domain_polarity.reindex(['domain', 'very_negative', 'negative' , 'slightly_negative', 'neutral','slightly_positive', 'positive', 'very_positive'], axis=1)
            domain_polarity = domain_polarity.fillna(0)
            print(domain_polarity)



            retweeted_collected = pd.read_sql_query("""
                     select 
                        ref_username as level,
                        count(*) as total, 
                        max(tweet_retweet_count),
                        max(retweeted_text) as text,
                        max(retweeted_tweet_id) as tweet_id
                    from tweet_main_table a, {0} b
                    where type ='retweeted' and a.tweet_tweet_id = b.tweet_tweet_id
                    group by level 
                    order by 2 desc 
                    limit 20
                    """.format(temp_table_name),engine)


            retweeted_global = pd.read_sql_query("""
                      select 
                        ref_username as level,
                        max(tweet_retweet_count) as total, 
                        max(tweet_retweet_count),
                        max(retweeted_text) as text,
                        max(retweeted_tweet_id) as tweet_id
                    from tweet_main_table a, {0} b
                    where type ='retweeted' and a.tweet_tweet_id = b.tweet_tweet_id
                    group by level 
                    order by 2 desc 
                    limit 20
                    """.format(temp_table_name),engine)


            replied_to = pd.read_sql_query("""
                      select 
                        ref_username as level,
                        count(*) as total, 
                        max(tweet_retweet_count),
                        max(retweeted_text) as text,
                        max(retweeted_tweet_id) as tweet_id
                    from tweet_main_table a, {0} b
                    where type ='replied_to' and a.tweet_tweet_id = b.tweet_tweet_id
                    group by level 
                    order by 2 desc 
                    limit 20
                    """.format(temp_table_name),engine)

            quoted = pd.read_sql_query("""
                     select 
                        ref_username as level,
                        count(*) as total, 
                        max(tweet_retweet_count),
                        max(retweeted_text) as text,
                        max(retweeted_tweet_id) as tweet_id
                    from tweet_main_table a, {0} b
                    where type ='quoted' and a.tweet_tweet_id = b.tweet_tweet_id
                    group by level 
                    order by 2 desc 
                    limit 20
                    """.format(temp_table_name),engine)

            entities = pd.read_sql_query("""
                     select 
                        lower(split_part(elem, '=', 2)) as level,
                        count(*) as total, 
                        max(retweeted_text) as text,
                        max(retweeted_tweet_id) as tweet_id
                    from
                        tweet_main_table t, {0} b,
                        unnest(string_to_array(t.domain_entities, ' || ')) WITH ORDINALITY a(elem, nr)
                    where t.tweet_tweet_id = b.tweet_tweet_id
                    group by lower(split_part(elem, '=', 2))
                    order by 2 desc 
                    limit 50
                    """.format(temp_table_name),engine)

            mentions = pd.read_sql_query("""
                    select 
                        lower(elem) as level,
                        count(*) as total, 
                        max(retweeted_text) as text,
                        max(retweeted_tweet_id) as tweet_id
                    from
                        tweet_main_table t,  {0} b,
                        unnest(string_to_array(t.mentions, '||')) WITH ORDINALITY a(elem, nr)
                    where  t.tweet_tweet_id = b.tweet_tweet_id
                    group by lower(elem)
                    order by 2 desc 
                    limit 20
                    """.format(temp_table_name),engine)

            hashtags = pd.read_sql_query("""
                     select 
                        lower(elem) as level,
                        count(*) as total, 
                        max(retweeted_text) as text,
                        max(retweeted_tweet_id) as tweet_id
                    from
                        tweet_main_table t,  {0} b,
                        unnest(string_to_array(t.hashtags, '||')) WITH ORDINALITY a(elem, nr)
                    where  t.tweet_tweet_id = b.tweet_tweet_id
                    group by lower(elem)
                    order by 2 desc 
                    limit 20
                    """.format(temp_table_name),engine)



        except Exception as e:
            print('error: dropping ', temp_table_name, str(e))
            conn.execute('drop table if exists {0}'.format(temp_table_name))

        print('dropping ', temp_table_name)
        conn.execute('drop table if exists {0}'.format(temp_table_name))
        conn.close()
        print(severity)
        return JsonResponse({'severity': severity.to_dict(orient='records'),
                             'subjectivity': subjectivity.to_dict(orient='records'),
                             'tweet_type': tweet_type.to_dict(orient='records'),
                             'domains': domains.to_dict(orient='records'),
                             'domain_polarity': domain_polarity.to_dict(orient='records'),
                             'retweeted_collected': retweeted_collected.to_dict(orient='records'),
                             'retweeted_global': retweeted_global.to_dict(orient='records'),
                             'replied_to': replied_to.to_dict(orient='records'),
                             'quoted': quoted.to_dict(orient='records'),
                             'entities': entities.to_dict(orient='records'),
                             'mentions': mentions.to_dict(orient='records'),
                             'hashtags': hashtags.to_dict(orient='records')})


def save_stopword(user, name, sw):
    stopwords_file = '/tmp/' + name + '.pckl'
    engine = create_engine(db_connection_url)
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
        engine.dispose()
        return 1
    except Exception as e:
        engine.dispose()
        print(e)
        return 0


def save_corrections(user, name, cor):
    cor_file = '/tmp/' + name + '.pckl'
    print('***********************************************', cor, ast.literal_eval(cor), type(ast.literal_eval(cor)))
    engine = create_engine(db_connection_url)
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
        engine.dispose()
        return 1
    except Exception as e:
        engine.dispose()
        print(e)
        return 0
    


def get_all_stopwords_files():
    files = ['default_stopwords']
    engine = create_engine(db_connection_url)
    try:
        
        table = pd.read_sql_query("""select distinct name from analyzer_stopword_files """, engine)
        for sw in table['name']:
            files.append(sw)
    except:
        print('///////////////////////////////////////////////// stopwords table not exist!')
    sw_default = stopwords.words('english')
    engine.dispose()
    return(files, sw_default)


def get_all_corrections_files():
    files = []
    engine = create_engine(db_connection_url)
    try:
        
        table = pd.read_sql_query("""select distinct name from analyzer_corrections_files """, engine)
        for cor in table['name']:
            files.append(cor)

    except:
        print('///////////////////////////////////////////////// stopwords table not exist!')
    engine.dispose()
    return(files)
        


def create_preprocess_tweets_job(user, name, tracker, preproc, nlp, stopwords, corrections):
    """
    This function takes the corresponding argument and:
        - creates an NLP instance and record it
        - creates a processor for repetative processing of tweets
    """
    print(user, name, tracker, preproc, nlp, stopwords, corrections)
    sw = True
    cor = True
    
    preproc = preproc.split(',')
    nlp = nlp.split(',')

    #Save to db
    errors = {}

    try:
        Processor_NLP.objects.create(user=user,
                                    name=name,
                                    tracker=tracker,
                                    preproc=preproc,
                                    nlp=nlp,
                                    stopwords=stopwords,
                                    corrections=corrections)
    except Exception as e:
        errors['Processor_NLP.objects.create'] = str(e)
    
    #Schedule the processor task
    try:
        schedule('analyzer.nlp_processor.Processor',
                        user_name=str(user),
                        proc_name=name,
                        tracker=tracker,
                        preproc=preproc,
                        nlp=nlp,
                        stopwords_file=stopwords,
                        corrections_file=corrections,
                        schedule_type='I',
                        minutes = 5,
                        repeats = 100000000
                        )
    except Exception as e:
        errors["schedule('analyzer.nlp_processor.Processor"] = str(e)

    if 'tagme' in preproc:
        try:
            print('Scheduling tagme......')
            schedule('analyzer.TagMeAnnotator.Annotator',
                            processor_name=name,
                            schedule_type='I',
                            minutes = 5,
                            repeats = 100000000
                            )
        except Exception as e:
            errors["schedule('analyzer.TagMeAnnotator.Annotator"] = str(e)
        
    return JsonResponse({'status': str(errors)})
       

def tweet_media_analyzer(request):
    return render(request, 'analyzer/tweet_media_analyzer.html')



def comparisor(request):
    return render(request, 'analyzer/comparisor.html')

def deepdiver(request):
    return render(request, 'analyzer/deepdiver.html')

def summarizer(request):
    return render(request, 'analyzer/summarizer.html')


def get_network_metrics(temp):
    tmp1 = temp[['from', 'from_name', 'from_size']]
    tmp2 = temp[['to', 'to_name', 'to_size']]
    tmp1.columns =['id', 'label', 'value']
    tmp2.columns =['id', 'label', 'value']
    distinct = pd.concat([tmp1, tmp2], axis=0)
    distinct.drop_duplicates(inplace=True)

    print(distinct, temp)

    G_symmetric = nx.Graph() 
    for index, row in temp.iterrows():
        G_symmetric.add_edge(row['from_name'], row['to_name'])

    degree_centrality = nx.degree_centrality(G_symmetric)
    betweenness_centrality = nx.betweenness_centrality(G_symmetric)
    eigen_centrality = nx.eigenvector_centrality(G_symmetric, max_iter=500)
    clustering = nx.clustering(G_symmetric)

    xx = dict(sorted(degree_centrality.items(), key=lambda item: item[1])) 
    yy = dict(sorted(betweenness_centrality.items(), key=lambda item: item[1])) 
    ie = dict(sorted(eigen_centrality.items(), key=lambda item: item[1])) 
    cl = dict(sorted(clustering.items(), key=lambda item: item[1])) 

    aa = []
    bb = []
    cc = []
    dd = []

    for i, v in enumerate(xx.keys()):
        aa.append([v,xx[v]])

    for i, v in enumerate(yy.keys()):
        bb.append([v,yy[v]])

    for i, v in enumerate(ie.keys()):
        cc.append([v,ie[v]])

    for i, v in enumerate(cl.keys()):
        dd.append([v,cl[v]])

    degree_df = pd.DataFrame(aa, columns=['label','value'])
    bet_df = pd.DataFrame(bb, columns=['label','value'])
    eigen = pd.DataFrame(cc, columns=['label','value'])
    clustering = pd.DataFrame(dd, columns=['label','value'])

    return distinct, degree_df, bet_df, eigen, clustering

@csrf_exempt
def save_dashboard(request):
    which = request.POST.get('which')
    elem = ''
    if which == 'track':
        elem = request.POST.get('track')
        elem = elem[:elem.rfind('(')]
    else:
        elem = request.POST.get('processor')

    engine = create_engine(db_connection_url)
    conn = engine.connect()
    df = pd.DataFrame([[int(request.user.id), which, elem]], columns=['user_id', 'which', 'elem'])
    try:
        conn.execute("""DELETE from dashboard_preferences where user_id = {0} and which ='{1}'""".format(int(request.user.id), which))
    except Exception as e:
        print(str(e))
    df.to_sql('dashboard_preferences', engine, if_exists='append', index=False)
    conn.close()
    engine.dispose()

@csrf_exempt
def get_dashboard_processor(request):
    print('GET PROCESSORS DASHBOARD: ', request.user, request.user.id)
    engine = create_engine(db_connection_url)
    table = pd.read_sql_query("""
        select a.id, a.name, a.tracker, a.stopwords, a.corrections, a.preproc, a.nlp, case when b.id is not null then 'Active' else 'Inactive' end status, a.user_id
        from analyzer_processor_nlp a left join django_q_schedule b on position(concat('''',a.name,'''')  in b.kwargs) > 0 and coalesce(repeats,0) <> 0
        and func = 'analyzer.nlp_processor.Processor'
            
        """.format(request.user.id), engine)
    procs = []
    for index, row in table.iterrows():
        procs.append([row['id'], row['name'],  row['tracker'], row['stopwords'], row['corrections'], row['preproc'], row['nlp'], row['status'],row['user_id']])
    engine.dispose()
    return JsonResponse(procs, safe=False) 