import time
from datetime import datetime
import jsonlines
from . import twitter_api, tweet_processor
import twitter
from sqlalchemy import create_engine
from django.conf import settings
import pandas as pd
import numpy as np

def TweetCollector(query, fetch_size, query_name, manual=True):

    counter = 0
   
    if not manual:
        json_response = twitter_api.gettw(query, fetch_size)
        main = tweet_processor.get_all_info(json_response['data'], json_response['includes'])
        insertTweets(main, query_name)
    


def insertTweets(main, query_name=''):
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
    
    df_merge['query_name'] = query_name
    df_users['query_name'] = query_name
    df_tweets_referenced['query_name'] = query_name
    df_tweets_referenced_meta['query_name'] = query_name
    df_annotations['query_name'] = query_name
    df_annotations['query_name'] = query_name
    df_annotation_domain['query_name'] = query_name
    df_annotation_entity['query_name'] = query_name
    df_entities['query_name'] = query_name
    df_media['query_name'] = query_name
    

    db_connection_url = "postgresql://{}:{}@{}:{}/{}".format(
    settings.DATABASES['default']['USER'],
    settings.DATABASES['default']['PASSWORD'],
    settings.DATABASES['default']['HOST'],
    settings.DATABASES['default']['PORT'],
    settings.DATABASES['default']['NAME'],
    )

    engine = create_engine(db_connection_url)

    print('*********************************************** INSERTED ***********************************************', df_media.columns)

    def_media =  df_media.replace(r'^\s*$', np.nan, regex=True)
    print('SHAPE: ', df_merge.shape)
            
    df_merge.drop('tweet_coordinate', axis=1, errors='ignore').to_sql('df_merge', engine, if_exists='append', index=False)
    

        
    df_users.to_sql('df_users', engine, if_exists='append', index=False)
    df_tweets_referenced.to_sql('df_tweets_referenced', engine, if_exists='append', index=False)
    df_tweets_referenced_meta.drop('coordinate', axis=1, errors='ignore').to_sql('df_tweets_referenced_meta', engine, if_exists='append', index=False)
    df_media.to_sql('df_media', engine, if_exists='append', index=False)
    df_annotations.to_sql('df_annotations', engine, if_exists='append', index=False)
    df_annotation_domain.to_sql('df_annotation_domain', engine, if_exists='append', index=False)
    df_annotation_entity.to_sql('df_annotation_entity', engine, if_exists='append', index=False)
    df_entities.to_sql('df_entities', engine, if_exists='append', index=False)

    
    conn = engine.connect() 
    try:
        print('inserting check')
        conn.execute('select tweet_tweet_id from tweet_main_table limit 1')
        print('inserting')
        df = pd.read_sql_query("""
            with base as (
                    select tweet_tweet_id, b.username, tweet_text, tweet_author_id, tweet_created_at, 
                    tweet_conversation_id, tweet_in_reply_to_user_id, 
                    tweet_retweet_count, tweet_reply_count, tweet_like_count, tweet_quote_count,
                    a.key, a.query_name
                    from df_merge a, df_users b
                    where a.query_name ='{0}' and a.key ='{1}'
                    and a.query_name = b.query_name and a.key = b.key and a.tweet_author_id = b.id
                ),
                base2 as (
                    with base as (
                        select distinct 
                            tweet_id, 
                            lower(domain_name) as domain_name, lower(entity_name) as entity_name
                        from df_annotations a, df_annotation_domain b, df_annotation_entity c
                        where a.query_name ='{0}' 
                        and a.key ='{1}'
                        and a.query_name = b.query_name and a.domain_id = b.domain_id
                        and a.query_name = c.query_name and a.entity_id = c.entity_id

                    )
                    select tweet_id, string_agg(concat(domain_name,'=',entity_name), ' || ') domain_entities
                    from base
                    group by tweet_id
                ),
                base3 as (
                    select tweet_id, string_agg(case when category = 'mentions' then username end,'||') mentions,
                    string_agg(case when category = 'hashtags' then tag end,'||') hashtags,
                    string_agg(case when category = 'annotations' and type_of ='Person' then normalized_text end,'||') annotation_persons,
                    string_agg(case when category = 'annotations' and type_of ='Organization' then normalized_text end,'||') annotation_org, 
                    string_agg(case when category = 'annotations' and type_of ='Product' then normalized_text end,'||') annotation_product,
                    string_agg(case when category = 'annotations' and type_of ='Place' then normalized_text end,'||') annotation_place,
                    string_agg(case when category = 'annotations' and type_of ='Other' then normalized_text end,'||') annotation_other
                    from df_entities
                    where query_name ='{0}' and key ='{1}'
                    group by tweet_id
                ),
                base4 as (
                    select 
                        a.tweet_id, type, username, reference_id, text,
                        string_agg(distinct case when type ='retweeted' then lower(username) end, ',') retweeted_user,
                        string_agg(distinct case when type ='quoted' then lower(username) end, ',') quoted_user,
                        string_agg(distinct case when type ='replied_to' then lower(username) end, ',') replied_to_user,
                        string_agg(distinct case when type ='retweeted' then a.reference_id  end, '||') retweeted_tweet_id,
                        b.text as retweeted_text
                    from 
                        df_tweets_referenced a, df_tweets_referenced_meta b, df_users c
                    where 
                        a.query_name ='{0}' and a.key ='{1}' and
                        a.query_name = b.query_name and b.query_name = c.query_name and
                        a.key = b.key and b.key = c.key and
                        a.reference_id = b.tweet_id and b.author_id = c.id 
                    group by a.tweet_id, type, username, reference_id, text
                ),
                base5 as (
                select base.*, base2.domain_entities, 
                mentions, hashtags, annotation_org, annotation_product, annotation_place, annotation_other, annotation_persons,
                retweeted_user, quoted_user, replied_to_user, retweeted_text, retweeted_tweet_id,
                type, base4.username as ref_username, text
                from base
                left join base2 on base.tweet_tweet_id = base2.tweet_id
                left join base3 on base.tweet_tweet_id = base3.tweet_id
                left join base4 on base.tweet_tweet_id = base4.tweet_id
                )
                select * from base5
            """.format(query_name, time_key), engine)
        print('from df to db')
        df.to_sql('tweet_main_table', engine, if_exists='append', index=False)
        print('inserted')
        print('deleting duplicates from entity and domain tables')
        conn.execute("""
            DELETE FROM df_annotation_entity a USING (
            SELECT MIN(ctid) as ctid, entity_id
                FROM df_annotation_entity 
                GROUP BY entity_id
                HAVING COUNT(*) > 1
            ) b
            WHERE a.entity_id = b.entity_id 
            AND a.ctid <> b.ctid
            ;

            DELETE FROM df_annotation_entity a USING (
            SELECT MIN(ctid) as ctid, entity_id
                FROM df_annotation_entity 
                GROUP BY entity_id
                HAVING COUNT(*) > 1
            ) b
            WHERE a.entity_id = b.entity_id 
            AND a.ctid <> b.ctid
            
            ;
        """)
        print('deleted')
    except:
        print('creating')
        conn.execute("""
            with base as (
                select tweet_tweet_id, b.username, tweet_text, tweet_author_id, tweet_created_at, 
                tweet_conversation_id, tweet_in_reply_to_user_id, 
                tweet_retweet_count, tweet_reply_count, tweet_like_count, tweet_quote_count,
                a.key, a.query_name
                from df_merge a, df_users b
                where a.query_name ='{0}' and a.key ='{1}'
                and a.query_name = b.query_name and a.key = b.key and a.tweet_author_id = b.id
            ),
            base2 as (
                with base as (
                    select distinct 
                        tweet_id, 
                        lower(domain_name) as domain_name, lower(entity_name) as entity_name
                    from df_annotations a, df_annotation_domain b, df_annotation_entity c
                    where a.query_name ='{0}' 
                    and a.key ='{1}'
                    and a.query_name = b.query_name and a.domain_id = b.domain_id
                    and a.query_name = c.query_name and a.entity_id = c.entity_id

                )
                select tweet_id, string_agg(concat(domain_name,'=',entity_name), ' || ') domain_entities
                from base
                group by tweet_id
            ),
            base3 as (
                select tweet_id, string_agg(case when category = 'mentions' then username end,'||') mentions,
                string_agg(case when category = 'hashtags' then tag end,'||') hashtags,
                string_agg(case when category = 'annotations' and type_of ='Person' then normalized_text end,'||') annotation_persons,
                string_agg(case when category = 'annotations' and type_of ='Organization' then normalized_text end,'||') annotation_org, 
                string_agg(case when category = 'annotations' and type_of ='Product' then normalized_text end,'||') annotation_product,
                string_agg(case when category = 'annotations' and type_of ='Place' then normalized_text end,'||') annotation_place,
                string_agg(case when category = 'annotations' and type_of ='Other' then normalized_text end,'||') annotation_other
                from df_entities
                where query_name ='{0}' and key ='{1}'
                group by tweet_id
            ),
            base4 as (
                select 
                     a.tweet_id, type, username, reference_id, text,
                    string_agg(distinct case when type ='retweeted' then lower(username) end, ',') retweeted_user,
                    string_agg(distinct case when type ='quoted' then lower(username) end, ',') quoted_user,
                    string_agg(distinct case when type ='replied_to' then lower(username) end, ',') replied_to_user,
                    string_agg(distinct case when type ='retweeted' then a.reference_id  end, '||') retweeted_tweet_id,
                    b.text as retweeted_text
                from 
                    df_tweets_referenced a, df_tweets_referenced_meta b, df_users c
                where 
                    a.query_name ='{0}' and a.key ='{1}' and
                    a.query_name = b.query_name and b.query_name = c.query_name and
                    a.key = b.key and b.key = c.key and
                    a.reference_id = b.tweet_id and b.author_id = c.id 
                group by a.tweet_id, type, username, reference_id, text
            ),
            base5 as (
            select base.*, base2.domain_entities, 
            mentions, hashtags, annotation_org, annotation_product, annotation_place, annotation_other, annotation_persons,
            retweeted_user, quoted_user, replied_to_user, retweeted_text, retweeted_tweet_id,
            type, base4.username as ref_username, text
            from base
            left join base2 on base.tweet_tweet_id = base2.tweet_id
            left join base3 on base.tweet_tweet_id = base3.tweet_id
            left join base4 on base.tweet_tweet_id = base4.tweet_id
            )
            SELECT * INTO tweet_main_table from base5
        """.format(query_name, time_key))
        print('created')
    print('dropping')
    conn.execute("""truncate
                    df_merge ,
                    df_users ,
                    df_tweets_referenced ,
                    df_tweets_referenced_meta ,
                    df_annotations ,
                    df_entities,
                    df_media
                """)
    print('dropped')
    conn.close()

    engine.dispose()