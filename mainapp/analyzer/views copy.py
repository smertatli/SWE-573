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
import networkx as nx

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
        return JsonResponse({'dates': dates})
    if which == 'get_processor_dates':
        arr = request.POST.get('processors')
        print(arr)
        if not arr:
            arr = 'null'
        table = pd.read_sql_query("""
            select distinct
                date(c.tweet_created_at) as collected_date
            from 
                df_tweets_processed a, analyzer_processor_nlp b, df_merge c
            where 
                a.processor_name = b.name and b.id in ({0}) and a.tweet_tweet_id = c.tweet_tweet_id
            order by
                1 
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
        nlp = request.POST.get('nlp')
        stopwords = request.POST.get('stopwords')
        corrections = request.POST.get('corrections')
        if not tracker:
            arr = 'null'
        return create_preprocess_tweets_job(request.user, name, tracker, preproc, nlp, stopwords, corrections)

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
        
        table = pd.read_sql_query("""
            select a.id, a.name, a.tracker, a.stopwords, a.corrections, a.preproc, a.nlp, case when b.id is not null then 'Active' else 'Inactive' end status
            from analyzer_processor_nlp a left join django_q_schedule b on position(a.name in b.kwargs) > 0 and coalesce(repeats,0) <> 0
            where a.user_id ='{0}' 
            """.format(request.user.id), engine)
        procs = []
        for index, row in table.iterrows():
            procs.append([row['id'], row['name'],  row['tracker'], row['stopwords'], row['corrections'], row['preproc'], row['nlp'], row['status']])
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
        word = pd.read_sql_query("""
                with base as (select distinct name from analyzer_processor_nlp where id in ({0}))
                SELECT b.name, elem,count(distinct tweet_Tweet_id) as freq
                FROM   df_tweets_processed t, base b,
                unnest(string_to_array(t.tweet_text, ' ')) WITH ORDINALITY a(elem, nr)
                where t.processor_name = b.name and elem > ''
                group by b.name, elem
                order by 3 desc
                limit 1000
                """.format(ids), engine)
        
        bigram = pd.read_sql_query("""
                with proc as (select distinct name from analyzer_processor_nlp where id in ({0})),
                base as (
                    SELECT b.name,tweet_Tweet_id, elem, nr
                    FROM   df_tweets_processed t,  proc b,
                    unnest(string_to_array(t.tweet_text, ' ')) WITH ORDINALITY a(elem, nr)
                    where t.processor_name = b.name
                ),
                base2 as (
                select b.name, concat(a.elem,' ', b.elem) as bigram, count(distinct a.tweet_tweet_id) as freq
                from base a, base b
                where a.tweet_tweet_id = b.tweet_tweet_id and a.nr + 1 = b.nr 
                and a.elem <> '' and b.elem <> ''
                group by b.name, concat(a.elem,' ', b.elem) 
                )
                select * from base2 order by freq desc limit 1000
                """.format(ids), engine)

        word_arr = []
        for index, row in word.iterrows():
            word_arr.append([row[0], row[1], row[2]]) 

        bigram_arr = []
        for index, row in bigram.iterrows():
            bigram_arr.append([row[0], row[1], row[2]]) 
        
        return JsonResponse({'word_count': word_arr, 'bigram': bigram_arr})  
       
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

    elif which == 'get_network_data':

        track = request.POST.get('track')
        domain = request.POST.get('domain')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        node_level = request.POST.get('node_level')

        if not domain:
            domain =''
        temp = ''
        if node_level == 'domain':
            
            temp = pd.read_sql_query(""" 
                with base as (
                    select 
                        distinct tweet_id
                    from 
                        df_annotations a, 
                        tracker_tracker b, 
                        df_merge c
                    where 
                        a.query_name = b.query_name 
                        and (a.domain_id::int in ({3} and b.id in ({0}) 
                        and a.tweet_id = c.tweet_tweet_id
                        and a.key = c.key
                        and date(c.tweet_created_at) between '{1}' and '{2}'
                ),
                base2 as (
                    select 
                        distinct a.tweet_id, a.domain_id
                    from 
                        df_annotations a, base b
                    where 
                        a.tweet_id = b.tweet_id and (a.domain_id::int not in ({3} 
                ),
                values as (
                    select domain_id, count(*) as node_size from base2 group by domain_id
                ),
                domains as (
                    select 
                        domain_id, max(lower(domain_name)) as domain_name 
                    from 
                        df_annotation_domain 
                    group by 
                        domain_id
                )
                select 
                    c.domain_name as from_name, c.domain_id as from, v1.node_size as from_size,
                    d.domain_name as to_name, d.domain_id as to, v2.node_size as to_size, 
                    count(*) as value
                from 
                    base2 a, 
                    base2 b, 
                    domains c, 
                    domains d,
                    values v1,
                    values v2
                where 
                    a.tweet_id = b.tweet_id 
                    and a.domain_id = c.domain_id 
                    and b.domain_id = d.domain_id
                    and c.domain_name < d.domain_name 
                    and a.domain_id = v1.domain_id 
                    and b.domain_id = v2.domain_id
                group by 
                    c.domain_name, 
                    d.domain_name,
                    c.domain_id, 
                    d.domain_id,
                    v1.node_size,
                    v2.node_size
                order by 
                    count(*) desc
                limit 2000
            """.format(track, start_date, end_date, (domain+'))') if domain > '' else "1) or 1=1)"), engine)
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
            
            xx = dict(sorted(degree_centrality.items(), key=lambda item: item[1])) 
            yy = dict(sorted(betweenness_centrality.items(), key=lambda item: item[1])) 
            
            aa = []
            bb = []
            for i, v in enumerate(xx.keys()):
                aa.append([v,xx[v]])
    
            for i, v in enumerate(yy.keys()):
                bb.append([v,yy[v]])
            
            degree_df = pd.DataFrame(aa, columns=['label','value'])
            bet_df = pd.DataFrame(bb, columns=['label','value'])

            return JsonResponse({'data': temp[['from', 'to', 'value']].to_dict(orient='records'), 
                                 'data2': distinct.to_dict(orient='records'),
                                 'degree_df': degree_df.to_json(orient='records'),
                                 'bet_df': bet_df.to_json(orient='records')})


        elif node_level == 'entity':
            
            temp = pd.read_sql_query("""
                with base as (
                     select 
                        tweet_id, entity_id, max(domain_id) as domain_id
                    from 
                        df_annotations a, 
                        tracker_tracker b, 
                        df_merge c
                    where 
                        a.query_name = b.query_name 
                        and (a.domain_id::int in ({3} and b.id in ({0}) 
                        and a.tweet_id = c.tweet_tweet_id
                        and a.key = c.key
                        and date(c.tweet_created_at) between '{1}' and '{2}'
                    group by
                        tweet_id, entity_id
                ),
                values as (select entity_id, count(*) node_size from base group by entity_id),
                entities as (select entity_id, max(lower(entity_name)) as entity_name from df_annotation_entity group by entity_id),
                domains as (select domain_id, max(lower(domain_name)) as domain_name from df_annotation_domain group by domain_id)
                select 
                    ent1.entity_name as from_name, ent1.entity_id as from, v1.node_size as from_size,
                    ent2.entity_name as to_name, ent2.entity_id as to, v2.node_size as to_size,
                    c.domain_name as from_domain, d.domain_name as to_domain, 
                    count(*) as value
                from 
                    base a, base b, domains c, domains d, entities ent1, entities ent2, values v1, values v2
                where 
                    a.tweet_id = b.tweet_id and ent1.entity_name < ent2.entity_name and 
                    a.domain_id = c.domain_id and b.domain_id = d.domain_id and
                    a.entity_id = ent1.entity_id and b.entity_id = ent2.entity_id and
                    a.entity_id = v1.entity_id and b.entity_id = v2.entity_id

                group by 
                    ent1.entity_name, ent2.entity_name, ent1.entity_id, ent2.entity_id, c.domain_name, d.domain_name, v1.node_size, v2.node_size
                order by 
                    count(*) desc
                limit 1000
            """.format(track, start_date, end_date, (domain+'))') if domain > '' else "1) or 1=1)"), engine)
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
            
            xx = dict(sorted(degree_centrality.items(), key=lambda item: item[1])) 
            yy = dict(sorted(betweenness_centrality.items(), key=lambda item: item[1])) 
            
            aa = []
            bb = []
            for i, v in enumerate(xx.keys()):
                aa.append([v,xx[v]])
    
            for i, v in enumerate(yy.keys()):
                bb.append([v,yy[v]])
            
            degree_df = pd.DataFrame(aa, columns=['label','value'])
            bet_df = pd.DataFrame(bb, columns=['label','value'])

            return JsonResponse({'data': temp[['from', 'to', 'value']].to_dict(orient='records'), 'data2': distinct.to_dict(orient='records'),
                                 'degree_df': degree_df.to_json(orient='records'),
                                 'bet_df': bet_df.to_json(orient='records')})
        elif node_level == 'hashtag':
            if domain == '':
                temp = pd.read_sql_query("""
                            with base as (
                                select distinct tweet_id, lower(tag) as tag 
                                from df_entities a, tracker_tracker b, df_merge c
                                where 
                                    a.tweet_id = c.tweet_tweet_id 
                                    and a.key=c.key 
                                    and a.query_name = b.query_name 
                                    and a.query_name = c.query_name
                                    and a.category='hashtags' 
                                    and b.id in ({0})
                                    and date(c.tweet_created_at) between '{1}' and '{2}'
                            ),
                            base2 as (
                                select tag, count(*) as node_size from base group by tag
                            ),
                            base3 as (
                                select tag, node_size, row_number() over (order by node_size desc) as id from base2
                            ),
                            base4 as (
                                select a.tag as from_name, c.id as from, c.node_size as from_size,
                                b.tag as to_name, d.id as to, d.node_size as to_size,
                                count(*) as value
                                from base a, base b, base3 c, base3 d
                                where 
                                    a.tweet_id = b.tweet_id 
                                    and a.tag < b.tag and
                                    a.tag = c.tag and
                                    b.tag = d.tag
                                group by a.tag, b.tag, c.id, d.id, c.node_size, d.node_size
                                order by count(*) desc
                            )
                            select *
                            from base4
                            limit 500
                        """.format(track, start_date, end_date),engine)
            else:
                temp = pd.read_sql_query("""
                            with base as (
                                select distinct tweet_id, lower(tag) as tag 
                                from df_entities a, tracker_tracker b, df_merge c
                                where 
                                    a.tweet_id = c.tweet_tweet_id 
                                    and a.key=c.key 
                                    and a.query_name = b.query_name 
                                    and a.query_name = c.query_name
                                    and a.category='hashtags' 
                                    and b.id in ({0})
                                    and date(c.tweet_created_at) between '{1}' and '{2}'
                            ),
                            base2 as (
                                select tag, count(*) as node_size from base group by tag
                            ),
                            domains as (
                                select distinct tweet_id 
                                from df_annotations a, tracker_tracker b 
                                where a.query_name = b.query_name and domain_id::int in ({3}) and b.id in ({0})
                            ),
                            base3 as (
                                select tag, node_size, row_number() over (order by node_size desc) as id from base2
                            ),
                            base4 as (
                                select a.tag as from_name, c.id as from, c.node_size as from_size,
                                b.tag as to_name, d.id as to, d.node_size as to_size,
                                count(*) as value
                                from base a, base b, base3 c, base3 d, domains e
                                where 
                                    a.tweet_id = b.tweet_id 
                                    and a.tweet_id = e.tweet_id
                                    and a.tag < b.tag and
                                    a.tag = c.tag and
                                    b.tag = d.tag
                                group by a.tag, b.tag, c.id, d.id, c.node_size, d.node_size
                                order by count(*) desc
                            )
                            select *
                            from base4
                            limit 300
                        """.format(track, start_date, end_date, domain),engine)
    
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
            
            xx = dict(sorted(degree_centrality.items(), key=lambda item: item[1])) 
            yy = dict(sorted(betweenness_centrality.items(), key=lambda item: item[1])) 
            
            aa = []
            bb = []
            for i, v in enumerate(xx.keys()):
                aa.append([v,xx[v]])
    
            for i, v in enumerate(yy.keys()):
                bb.append([v,yy[v]])
            
            degree_df = pd.DataFrame(aa, columns=['label','value'])
            bet_df = pd.DataFrame(bb, columns=['label','value'])

            return JsonResponse({'data': temp[['from', 'to', 'value']].to_dict(orient='records'), 'data2': distinct.to_dict(orient='records'),
                                 'degree_df': degree_df.to_json(orient='records'),
                                 'bet_df': bet_df.to_json(orient='records')})
  
        elif node_level == 'mention':
            if domain != '':
                temp = pd.read_sql_query("""
                            with base as (
                                    select lower(d.username) as from_user, lower(a.username) as to_user, count(*) as value
                                    from 
                                        df_entities a, tracker_tracker b, df_merge c, 
                                        (
                                            select a.id as user_id, max(username) as username 
                                            from df_users a, tracker_tracker b 
                                            where a.query_name = b.query_name and b.id in ({0})
                                            group by a.id
                                        ) d,
                                        df_annotations e
                                    where 
                                        a.query_name = e.query_name 
                                        and e.domain_id::int in ({3})
                                        and a.tweet_id = c.tweet_tweet_id 
                                        and a.key=c.key 
                                        and a.query_name = c.query_name
                                        and a.query_name = b.query_name 
                                        and c.tweet_author_id::bigint = d.user_id::bigint
                                        and a.category='mentions' 
                                        and b.id in ({0})
                                        and date(c.tweet_created_at) between '{1}' and '{2}'
                                        and c.tweet_tweet_id = e.tweet_id
                                        and e.key = c.key
                                    group by
                                        lower(d.username), lower(a.username)
                                    order by 
                                        count(*) desc
                                    limit 500
                                ),
                                ids as (select distinct from_user as user from base union select distinct to_user as user from base),
                                ids_rank as (select *, row_number() over (order by user) as id from ids)
                            select 
                                a.from_user as from_name, b.id as from, a.to_user as to_name, c.id as to, value
                            from 
                                base a, ids_rank b, ids_rank c
                            where 
                                a.from_user = b.user and a.to_user = c.user


                        """.format(track, start_date, end_date, domain),engine)
            else:
                temp = pd.read_sql_query("""
                            with base as (
                                    select lower(d.username) as from_user, lower(a.username) as to_user, count(*) as value
                                    from 
                                        df_entities a, tracker_tracker b, df_merge c, 
                                        (
                                            select a.id as user_id, max(username) as username 
                                            from df_users a, tracker_tracker b 
                                            where a.query_name = b.query_name and b.id in ({0})
                                            group by a.id
                                        ) d
                                    where 
                                        a.tweet_id = c.tweet_tweet_id 
                                        and a.key=c.key 
                                        and a.query_name = c.query_name
                                        and a.query_name = b.query_name 
                                        and c.tweet_author_id::bigint = d.user_id::bigint
                                        and a.category='mentions' 
                                        and b.id in ({0})
                                        and date(c.tweet_created_at) between '{1}' and '{2}'
                                    group by
                                        lower(d.username), lower(a.username)
                                    order by 
                                        count(*) desc
                                    limit 500
                                ),
                                ids as (select distinct from_user as user from base union select distinct to_user as user from base),
                                ids_rank as (select *, row_number() over (order by user) as id from ids)
                            select 
                                a.from_user as from_name, b.id as from, a.to_user as to_name, c.id as to, value
                            from 
                                base a, ids_rank b, ids_rank c
                            where 
                                a.from_user = b.user and a.to_user = c.user


                        """.format(track, start_date, end_date),engine)

    
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
            
            xx = dict(sorted(degree_centrality.items(), key=lambda item: item[1])) 
            yy = dict(sorted(betweenness_centrality.items(), key=lambda item: item[1])) 
            
            aa = []
            bb = []
            for i, v in enumerate(xx.keys()):
                aa.append([v,xx[v]])
    
            for i, v in enumerate(yy.keys()):
                bb.append([v,yy[v]])
            
            degree_df = pd.DataFrame(aa, columns=['label','value'])
            bet_df = pd.DataFrame(bb, columns=['label','value'])

            return JsonResponse({'data': temp[['from', 'to', 'value']].to_dict(orient='records'), 'data2': distinct.to_dict(orient='records'),
                                 'degree_df': degree_df.to_json(orient='records'),
                                 'bet_df': bet_df.to_json(orient='records')})
        elif node_level == 'mention_cooccurrence':
            if domain == '':
                temp = pd.read_sql_query("""
                            with base as (
                                    select distinct
                                        a.tweet_id, lower(username) as username
                                    from 
                                        df_entities a, tracker_tracker b, df_merge c
                                    where 
                                        a.tweet_id = c.tweet_tweet_id 
                                        and a.key=c.key 
                                        and a.query_name = c.query_name
                                        and a.query_name = b.query_name 
                                        and a.category='mentions' 
                                        and b.id in ({0})
                                        and date(c.tweet_created_at) between '{1}' and '{2}'
                                ),
                                ids as (select distinct username from base),
                                ids_rank as (select username, row_number() over (order by user) as id from ids)
                            select 
                                a.username as from_name, c.id as from, b.username as to_name, d.id as to, count(*) as value
                            from 
                                base a, base b, ids_rank c, ids_rank d
                            where 
                                a.tweet_id = b.tweet_id and a.username < b.username 
                                and a.username = c.username and b.username = d.username
                            group by
                                a.username, c.id, b.username, d.id
                            order by
                                count(*) desc
                            limit
                                300


                        """.format(track, start_date, end_date),engine)
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
                
                xx = dict(sorted(degree_centrality.items(), key=lambda item: item[1])) 
                yy = dict(sorted(betweenness_centrality.items(), key=lambda item: item[1])) 
                
                aa = []
                bb = []
                for i, v in enumerate(xx.keys()):
                    aa.append([v,xx[v]])
        
                for i, v in enumerate(yy.keys()):
                    bb.append([v,yy[v]])
                
                degree_df = pd.DataFrame(aa, columns=['label','value'])
                bet_df = pd.DataFrame(bb, columns=['label','value'])

                return JsonResponse({'data': temp[['from', 'to', 'value']].to_dict(orient='records'), 'data2': distinct.to_dict(orient='records'),
                                    'degree_df': degree_df.to_json(orient='records'),
                                    'bet_df': bet_df.to_json(orient='records')})

        elif node_level == 'bigram':
            if domain == '':
                temp = pd.read_sql_query("""

                    with base as (
                        SELECT tweet_Tweet_id, elem, nr
                        FROM   df_tweets_processed t, 
                        unnest(string_to_array(t.tweet_text, ' ')) WITH ORDINALITY a(elem, nr)
                    ),
                    base2 as (
                    select distinct a.tweet_tweet_id, concat(a.elem,' ', b.elem) as bigram,a.elem el1, b.elem el2
                    from base a, base b
                    where a.tweet_tweet_id = b.tweet_tweet_id and a.nr + 1 = b.nr 
                    and a.elem <> '' and b.elem <> ''
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
                        limit 1000
                    )
                    select from_name, to_name, value, v1.node_size as from_size, v2.node_size as to_size, i1.id as from, i2.id as to
                    from calcs, values as v1, values as v2, ids as i1, ids as i2
                    where calcs.from_name = v1.bigram and calcs.to_name = v2.bigram and calcs.from_name = i1.bigram and calcs.to_name = i2.bigram 
                """, engine)

                tmp1 = temp[['from', 'from_name', 'from_size']]
                tmp2 = temp[['to', 'to_name', 'to_size']]
                tmp1.columns =['id', 'label', 'value']
                tmp2.columns =['id', 'label', 'value']
                distinct = pd.concat([tmp1, tmp2], axis=0)
                distinct.drop_duplicates(inplace=True)
                
                G_symmetric = nx.Graph() 
                for index, row in temp.iterrows():
                    G_symmetric.add_edge(row['from_name'], row['to_name'])
                
                degree_centrality = nx.degree_centrality(G_symmetric)
                betweenness_centrality = nx.betweenness_centrality(G_symmetric)
                
                xx = dict(sorted(degree_centrality.items(), key=lambda item: item[1])) 
                yy = dict(sorted(betweenness_centrality.items(), key=lambda item: item[1])) 
                
                aa = []
                bb = []
                for i, v in enumerate(xx.keys()):
                    aa.append([v,xx[v]])
        
                for i, v in enumerate(yy.keys()):
                    bb.append([v,yy[v]])
                
                degree_df = pd.DataFrame(aa, columns=['label','value'])
                bet_df = pd.DataFrame(bb, columns=['label','value'])

                return JsonResponse({'data': temp[['from', 'to', 'value']].to_dict(orient='records'), 'data2': distinct.to_dict(orient='records'),
                                                 'degree_df': degree_df.to_json(orient='records'),
                                                 'bet_df': bet_df.to_json(orient='records')})


    elif which == 'domain_top_entities_graph':
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
        return JsonResponse(arr, safe=False)
    elif which == 'get_comparisons_metrics':
        source1 = request.POST.get('source1')
        source2 = request.POST.get('source2')
        start_date1 = request.POST.get('start_date1')
        start_date2 = request.POST.get('start_date2')
        end_date1 = request.POST.get('end_date1')
        end_date2 = request.POST.get('end_date2')
        level = request.POST.get('level')
        if level == 'mentions' or level == 'hashtags':
            temp = pd.read_sql_query("""
                    with periods as (
                        select distinct tweet_tweet_id, case when (b.id in ({0}) and created_at between '{1}' and '{2}') then 0 else 1 end as period, 
                        polarity, multiplier
                        
                        from df_tweets_processed a, analyzer_processor_nlp b
                        where 
                            ((b.id in ({0}) and created_at between '{1}' and '{2}') or (b.id in ({3}) and created_at between '{4}' and '{5}'))
                            and a.processor_name = b.name
                    ),
                    tags as (
                        select distinct a.*, lower({7}) as tag
                        from periods a, df_entities b
                        where a.tweet_tweet_id = b.tweet_id and b.category = '{6}' 
                    ),
                    agg as (
                        select tag, avg(period) as freq, count(distinct tweet_tweet_id) as total, sum(polarity*multiplier)/sum(multiplier) as polarity_avg,
                        avg(case when period = 0 then polarity end) polarity_avg_period1,
                        avg(case when period = 1 then polarity end) polarity_avg_period2
                        from tags
                        group by tag
                    ),
                    all_data as (
                        select 
                            tag, 
                            freq,
                            total,
                            case when polarity_avg_period1 is null then 0 else polarity_avg_period1 end as polarity_avg_period1,
                            case when polarity_avg_period2 is null then 0 else polarity_avg_period2 end as polarity_avg_period2,
                            (total*(1-freq))::int total_period1, 
                            row_number() over (order by case when total*(1-freq) > 0 then total*(1-freq) else 0 end desc) as rank_period1, 
                            (total*freq)::int total_period2, 
                            row_number() over (order by case when total*freq > 0 then total*freq else 0 end desc) as rank_period2, 
                            row_number() over (order by case when freq = 0 then total*(1-freq) else 0 end desc) as rank_period1_only, 
                            row_number() over (order by case when 1-freq = 0 then total*freq else 0 end desc) as rank_period2_only
                        from agg  
                    ) 
                    
                        select *
                        from all_data where rank_period1 <= 50 or rank_period2 <= 50  or rank_period1_only <= 50 or rank_period2_only <= 50
                    
                    """.format(source1, start_date1, end_date1,source2, start_date2, end_date2, level, 'username' if level=='mentions' else 'tag'), engine)
            
            return JsonResponse(temp.to_dict(orient='row'), safe=False)
        elif level == 'domain':
            temp = pd.read_sql_query("""
                    with periods as (
                        select distinct tweet_tweet_id, case when (b.id in ({0}) and created_at between '{1}' and '{2}') then 0 else 1 end as period, 
                        polarity, multiplier
                        
                        from df_tweets_processed a, analyzer_processor_nlp b
                        where 
                            ((b.id in ({0}) and created_at between '{1}' and '{2}') or (b.id in ({3}) and created_at between '{4}' and '{5}'))
                            and a.processor_name = b.name
                    ),
                    tags as (
                        select distinct domain_name, a.period, a.polarity, a.multiplier, lower({7}) as tag
                        from periods a, df_annotations b, (select domain_id, max(domain_name) as domain_name from df_annotation_domain group by domain_id) c
                        where a.tweet_tweet_id = b.tweet_id and b.domain_id = c.domain_id
                    ),
                    agg as (
                        select tag, avg(period) as freq, count(distinct tweet_tweet_id) as total, sum(polarity*multiplier)/sum(multiplier) as polarity_avg,
                        avg(case when period = 0 then polarity end) polarity_avg_period1,
                        avg(case when period = 1 then polarity end) polarity_avg_period2
                        from tags
                        group by tag
                    ),
                    all_data as (
                        select 
                            tag, 
                            freq,
                            total,
                            case when polarity_avg_period1 is null then 0 else polarity_avg_period1 end as polarity_avg_period1,
                            case when polarity_avg_period2 is null then 0 else polarity_avg_period2 end as polarity_avg_period2,
                            (total*(1-freq))::int total_period1, 
                            row_number() over (order by case when total*(1-freq) > 0 then total*(1-freq) else 0 end desc) as rank_period1, 
                            (total*freq)::int total_period2, 
                            row_number() over (order by case when total*freq > 0 then total*freq else 0 end desc) as rank_period2, 
                            row_number() over (order by case when freq = 0 then total*(1-freq) else 0 end desc) as rank_period1_only, 
                            row_number() over (order by case when 1-freq = 0 then total*freq else 0 end desc) as rank_period2_only
                        from agg  
                    ) 
                    
                        select *
                        from all_data where rank_period1 <= 50 or rank_period2 <= 50  or rank_period1_only <= 50 or rank_period2_only <= 50
                    
                    """.format(source1, start_date1, end_date1,source2, start_date2, end_date2, level, 'username' if level=='mentions' else 'tag'), engine)
            
            return JsonResponse(temp.to_dict(orient='row'), safe=False)
    
    elif which == 'cancel_processor':
        ids = request.POST.get('selected')
        try:
            conn = engine.connect()
            print('DELETING ', ids)
            conn.execute("DELETE from analyzer_processor_nlp where id in ({0})".format(ids))
            return JsonResponse({'result':'OK'})
        except Exception as e:
            
            return JsonResponse({'result':'NOK'})
        



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
                        minutes = 1,
                        repeats = 100000000
                        )
    except Exception as e:
        errors["schedule('analyzer.nlp_processor.Processor"] = str(e)
        
    return JsonResponse({'status': str(errors)})
       

def tweet_media_analyzer(request):
    return render(request, 'analyzer/tweet_media_analyzer.html')



def comparisor(request):
    return render(request, 'analyzer/comparisor.html')