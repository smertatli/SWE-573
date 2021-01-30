def Annotator(processor_name):

    from django.shortcuts import render
    from django.http import JsonResponse, HttpResponse
    from django.views.decorators.csrf import csrf_exempt
    import sys
    from sqlalchemy import create_engine
    from django.conf import settings
    import pandas as pd
    import numpy as np 
    import preprocessor as p
    import ast
    from textblob import TextBlob
    import nltk
    from nltk.corpus import stopwords
    import string
    import datetime
    import requests

    db_connection_url = "postgresql://{}:{}@{}:{}/{}".format(
    settings.DATABASES['default']['USER'],
    settings.DATABASES['default']['PASSWORD'],
    settings.DATABASES['default']['HOST'],
    settings.DATABASES['default']['PORT'],
    settings.DATABASES['default']['NAME'],
    )

    engine = create_engine(db_connection_url)

    MY_GCUBE_TOKEN = '8a5f5e3b-a45d-4152-a8f5-6718390824e3-843339462'

    query = 'https://tagme.d4science.org/tagme/tag?lang=en&gcube-token={0}&text='.format(MY_GCUBE_TOKEN)


    annotation_table_exists = True 
    processor_table_exists = True 
    try:
        processed_tweets = pd.read_sql_query('select * from tweet_tagme_annotation limit 1')
    except:
        print('creating annotation table for the first time')
        annotation_table_exists = False

    try:    
        processed_tweets = pd.read_sql_query('select * from df_tweets_processed limit 1')
    except:
        print('waiting for processor table to create')
        processor_table_exists = False

    if processor_table_exists:
        if annotation_table_exists:
            processed_tweets = pd.read_sql_query("""
                    select a.tweet_tweet_id, a.tweet_text 
                    from df_tweets_processed a
                    left join tweet_tagme_annotation b on a.tweet_tweet_id = tweet_tweet_id
                    where b.tweet_tweet_id is null and a.processor_name = {0}
                    limit 20000""".format(processor_name))
        else:
            conn = engine.connect()
            processed_tweets = pd.read_sql_query("""
                    select a.tweet_tweet_id, a.tweet_text 
                    from df_tweets_processed a
                    where a.processor_name = {0}
                    limit 20000""".format(processor_name))

        processed_tweets['annotations'] = ''
        
        for index, row in processed_tweets.iterrows():
            try:
                receive = requests.get(query+row['tweet_text'])
                for a in receive.json()['annotations']:
                    if a['rho'] >= 0.3:
                        row['annotations'] = row['annotations'] + '||' + str(a['rho']) +'='+a['title']
            except:
                print('error in tagging. tweet id = ', row['tweet_tweet_id'])

        processed_tweets.to_sql('tweet_tagme_annotation', engine, if_exists='append', index=False)
        conn.close()
        engine.dispose()
    else:
        print('skipping')

    

    


    


    
    
 
   
    



 
    


    