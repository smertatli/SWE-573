def Processor(user_name, proc_name, tracker, preproc, nlp, stopwords_file, corrections_file):

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

    db_connection_url = "postgresql://{}:{}@{}:{}/{}".format(
    settings.DATABASES['default']['USER'],
    settings.DATABASES['default']['PASSWORD'],
    settings.DATABASES['default']['HOST'],
    settings.DATABASES['default']['PORT'],
    settings.DATABASES['default']['NAME'],
    )

    engine = create_engine(db_connection_url)
    
    print( user_name, proc_name, tracker, preproc, nlp, stopwords_file, corrections_file)


    dict = {}
    dict['tweet_id'] = ''
    dict['text_cleaned'] = ''
    dict['sentiment'] = 0.1
    dict['polarity'] = 0.1
    table = pd.DataFrame(dict, index=[0])
    #table.to_sql('df_users', engine, if_exists='append', index=False)


    table = pd.read_sql_query("""
        select distinct
            a.tweet_tweet_id, tweet_text
        from
            df_merge a, tracker_tracker b
        where
            a.query_name = b.query_name 
            and tweet_lang = 'en'
            and tweet_text not like 'RT @%'
            and b.id in ({0})

        union 

        select distinct 
            tweet_id, text 
        from 
            df_tweets_referenced_meta a, tracker_tracker b
        where 
            a.query_name = b.query_name 
            and a.lang = 'en'
            and b.id in ({0})
    """.format(tracker), engine)

    
    
    args = ''
    if 'remove_punc' in preproc:
        args = args + 'p.OPT.EMOJI, p.OPT.SMILEY' + ','
    if 'remove_urls' in preproc:
        args = args + 'p.OPT.URL' + ','
    if 'remove_hashtags' in preproc:
        args = args + 'ap.OPT.HASHTAG' + ','
    if 'remove_mentions' in preproc:
        args = args + 'p.OPT.MENTION' + ','
    if 'remove_reserved' in preproc:
        args = args + 'p.OPT.RESERVED' + ','
    if 'remove_numbers' in preproc:
        args = args + 'p.OPT.NUMBER' + ','
    args  = 'p.set_options(' + args[0:-1] +')'

    ast.literal_eval(args)
    print(args)
    
    
    
    
    


    #p.clean('Preprocessor is #awesome 👍 https://github.com/s/preprocessor')
    


    
    
 
   
    



 
    


    