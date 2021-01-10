import time
from datetime import datetime
import jsonlines
from . import twitter_api, tweet_processor
import twitter
from sqlalchemy import create_engine
from django.conf import settings
import pandas as pd

def TweetCollector(query, fetch_size, manual=True):

    counter = 0
   
    if not manual:
        json_response = twitter_api.gettw(query, fetch_size)
        main = tweet_processor.get_all_info(json_response['data'], json_response['includes'])
        insertTweets(main)
    else:
        df_merge, df_users, df_tweets_referenced, df_tweets_referenced_meta, \
                        df_media, df_annotations, df_annotation_entity, df_annotation_domain, df_entities = [],[],[],[],[],[],[],[],[]
        with jsonlines.open('./tracker/tweet_db.json', mode='r') as file:
            for line in file.iter():
                counter += 1
                
                try:
                    data = line['data']
                    includes = line['includes']
                    main = tweet_processor.get_all_info(data, includes)

                    df_merge.append(main[0])
                    df_users.append(main[1])
                    df_tweets_referenced.append(main[2])
                    df_tweets_referenced_meta.append(main[3])
                    df_media.append(main[4])
                    df_annotations.append(main[5][0])
                    df_annotation_domain.append(main[5][1])
                    df_annotation_entity.append(main[5][2])
                    df_entities.append(main[6])
  
                except Exception as e:
                    print('-----------------------------------------------------------ERROR: ', str(e), ', at line: ', str(counter))
                    continue

                if counter % 500 == 0:
        
                    merged_all = pd.concat(df_merge, axis=0).reset_index(drop=True)
                    referenced_meta_all = pd.concat(df_tweets_referenced_meta, axis=0)
                    referenced_all = pd.concat(df_tweets_referenced, axis=0)
                    users_all = pd.concat(df_users, axis=0)
                    media_all = pd.concat(df_media, axis=0)
                    annotation_all = pd.concat(df_annotations, axis=0)
                    annotation_entity_all = pd.concat(df_annotation_entity, axis=0)
                    annotation_domain_all = pd.concat(df_annotation_domain, axis=0)
                    entities_all = pd.concat(df_entities, axis=0)

                    df_merge, df_users, df_tweets_referenced, df_tweets_referenced_meta, \
                        df_media, df_annotations, df_annotation_entity, df_annotation_domain, df_entities = [],[],[],[],[],[],[],[],[]

                    insertTweets((merged_all, users_all, referenced_all, referenced_meta_all, media_all,
                                    (annotation_all, annotation_domain_all, annotation_entity_all), entities_all))






def insertTweets(main):
    time_key = datetime.now()
    
    for elem in main:
        print(type(elem))
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

    print('*********************************************** INSERTED ***********************************************')

    print('SHAPE: ', df_merge.shape)
#    for i in range(0,df_merge.shape[0]):
#        
#        try:
#            df_merge.loc[i:i+1, :].to_sql('df_merge', engine, if_exists='append', index=False)
#        except:
#            print('ERROR: ', df_merge.loc[i:i+1, :])
#            df_merge.loc[i:i+1, :].to_csv('incele.csv')
            
    df_merge.drop('tweet_coordinate', axis=1, errors='ignore').to_sql('df_merge', engine, if_exists='append', index=False)
    

        
    df_users.to_sql('df_users', engine, if_exists='append', index=False)
    df_tweets_referenced.to_sql('df_tweets_referenced', engine, if_exists='append', index=False)
    df_tweets_referenced_meta.drop('coordinate', axis=1, errors='ignore').to_sql('df_tweets_referenced_meta', engine, if_exists='append', index=False)
    df_media.to_sql('df_media', engine, if_exists='append', index=False)
    df_annotations.to_sql('df_annotations', engine, if_exists='append', index=False)
    df_annotation_domain.to_sql('df_annotation_domain', engine, if_exists='append', index=False)
    df_annotation_entity.to_sql('df_annotation_entity', engine, if_exists='append', index=False)
    df_entities.to_sql('df_entities', engine, if_exists='append', index=False)