import time
from datetime import datetime
import jsonlines
from . import twitter_api, tweet_processor
import twitter
from sqlalchemy import create_engine
from django.conf import settings
import pandas as pd

def TweetCollector():

    counter = 0
   
    json_response = twitter_api.gettw()
    main = tweet_processor.get_all_info(json_response['data'], json_response['includes'])
    print('----------------',main)
    time_key = datetime.now()
    
    for elem in main:
        if isinstance(elem, tuple):
            for el in elem:
                el['key'] = time_key
                break
        else:
            elem['key'] = time_key

    df_merge = main[0]
    df_users = main[1]
    df_tweets_referenced = main[2]
    df_tweets_referenced_meta = main[3]
    df_media = main[4]
    df_annotations = main[5][0]
    df_annotation_domain = main[5][1]
    df_annotation_entity = main[5][2]
    df_entities = main[6]

    df_tweets_referenced.columns  =['tweet_id', 'type', 'reference_tweet_id', 'key']
    
    db_connection_url = "postgresql://{}:{}@{}:{}/{}".format(
    settings.DATABASES['default']['USER'],
    settings.DATABASES['default']['PASSWORD'],
    settings.DATABASES['default']['HOST'],
    settings.DATABASES['default']['PORT'],
    settings.DATABASES['default']['NAME'],
    )

    engine = create_engine(db_connection_url)

    print('**********************ANANANANANANA***********************')
    df_merge.to_sql('df_merge', engine, if_exists='append', index=False)
    df_users.to_sql('df_users', engine, if_exists='append', index=False)
    df_tweets_referenced.to_sql('df_tweets_referenced', engine, if_exists='append', index=False)
    df_tweets_referenced_meta.to_sql('df_tweets_referenced_meta', engine, if_exists='append', index=False)
    df_media.to_sql('df_media', engine, if_exists='append', index=False)
    df_annotations.to_sql('df_annotations', engine, if_exists='append', index=False)
    df_annotation_domain.to_sql('df_annotation_domain', engine, if_exists='append', index=False)
    df_annotation_entity.to_sql('df_annotation_entity', engine, if_exists='append', index=False)
    df_entities.to_sql('df_entities', engine, if_exists='append', index=False)

