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
    from textblob import TextBlob
    import nltk
    nltk.download('punkt')
    nltk.download('averaged_perceptron_tagger')
    nltk.download('brown')
    from nltk.corpus import stopwords
    import string
    import datetime


    db_connection_url = "postgresql://{}:{}@{}:{}/{}".format(
    settings.DATABASES['default']['USER'],
    settings.DATABASES['default']['PASSWORD'],
    settings.DATABASES['default']['HOST'],
    settings.DATABASES['default']['PORT'],
    settings.DATABASES['default']['NAME'],
    )

    engine = create_engine(db_connection_url)
    
    print( user_name, proc_name, tracker, preproc, stopwords_file, corrections_file)


    dict = {}
    dict['tweet_id'] = ''
    dict['text_cleaned'] = ''
    dict['sentiment'] = 0.1
    dict['polarity'] = 0.1
  
    try:
        if stopwords_file == 'default_stopwords':
            stopwords = stopwords.words('english')
        else:
            stopwords = pd.read_pickle('/usr/src/mainapp/' + stopwords_file + '.pckl' )
        print('SUCCESSFUL OPEN STOPWORDS', '/usr/src/mainapp/' + stopwords_file + '.pckl')
    except Exception as e:
        stopwords = []
        print('CANNOT OPEN STOPWORDS', '/usr/src/mainapp/' + stopwords_file + '.pckl', str(e))
    try:
        corrections = pd.read_pickle('/usr/src/mainapp/' + corrections_file + '.pckl' )
        print('SUCCESSFUL OPEN CORRECTİONS', '/usr/src/mainapp/' + corrections_file + '.pckl', corrections)
    except:
        corrections = []
        print('CANNOT OPEN CORRECTİONS', '/usr/src/mainapp/' + corrections_file + '.pckl')

    id_string = ''
    noTable = False
    check = pd.DataFrame()
    try:
        now = datetime.datetime.now()
        print('MINUTE: ', str(now.minute))
        if now.minute % 2 == 0:
            conn = engine.connect()
            
            try:
                conn.execute("""
                        DELETE FROM df_tweets_processed a USING (
                        SELECT MIN(ctid) as ctid, processor_name, tweet_tweet_id
                            FROM df_tweets_processed 
                            GROUP BY processor_name, tweet_tweet_id 
                            HAVING COUNT(*) > 1
                        ) b
                        WHERE a.tweet_tweet_id = b.tweet_tweet_id and  a.processor_name = b.processor_name
                        AND a.ctid <> b.ctid
                """)
                print('DELETING DUPLICATES: SUCCESS')
            except Exception as e:
                print('DELETING DUPLICATES: ', str(e))
            conn.close()

        check = pd.read_sql_query("""
                with base as (
                    select distinct tweet_tweet_id from df_merge 
                    where query_name in (select distinct query_name from tracker_tracker where id in ({0}))
                    and tweet_text not like 'RT%'
                    union 
                    select distinct tweet_id from df_tweets_referenced_meta  
                    where query_name in (select distinct query_name from tracker_tracker where id in ({0}))
                )
                select distinct a.tweet_tweet_id
                from base a left join df_tweets_processed b on a.tweet_tweet_id = b.tweet_tweet_id and processor_name in ('{1}')
                where b.tweet_tweet_id is null 
                limit 50000
            """.format(tracker, proc_name), engine)
        id_string = ",".join(["'"+txt+"'" for txt in check['tweet_tweet_id']])
    except:
        noTable = True
    

    if id_string == '' and not noTable:
        print('Skipping, no new tweets detected...')
    else:
        if noTable:
            print('Creating processed_tweets table for the first time...')
        
        if not check.empty:
            print('KONTROL ', check)
            print('Inserting ', len(check['tweet_tweet_id']), ' rows...')
        for remainder in range(0,10):
            table = pd.read_sql_query("""
                with base as (
                    select distinct
                        a.tweet_tweet_id, tweet_text, null as name, date(tweet_created_at) as created_at, 1 as multiplier
                    from
                        df_merge a, tracker_tracker b
                    where
                        a.query_name = b.query_name 
                    
                        and tweet_text not like 'RT @%'
                        and b.id in ({0})

                    union 

                    select distinct 
                        a.tweet_id, text, null as name, date(created_at) as created_at, count(distinct c.tweet_id) + 1 as multiplier
                    from 
                        df_tweets_referenced_meta a, tracker_tracker b, df_tweets_referenced c
                    where 
                        a.query_name = b.query_name and a.tweet_id = c.reference_id and a.key = c.key and a.query_name = c.query_name
                        and b.id in ({0})
                    group by
                        a.tweet_id, text, name, date(created_at)
                    )
                    select * from base where mod(tweet_tweet_id::bigint,10) = {1} and (tweet_tweet_id in ({2}) or {3})
            """.format(tracker, remainder, "'1'" if id_string == '' else id_string, ' 1=1' if check.empty else ' 1=2' ), engine)

            if table.shape[0] > 0:
                punc = False
                args = ''
                if 'remove_punc' in preproc:
                    args = args + 'p.OPT.EMOJI, p.OPT.SMILEY' + ','
                    punc = True
                if 'remove_urls' in preproc:
                    args = args + 'p.OPT.URL' + ','
                if 'remove_hashtags' in preproc:
                    args = args + 'p.OPT.HASHTAG' + ','
                if 'remove_mentions' in preproc:
                    args = args + 'p.OPT.MENTION' + ','
                if 'remove_reserved' in preproc:
                    args = args + 'p.OPT.RESERVED' + ','
                if 'remove_numbers' in preproc:
                    args = args + 'p.OPT.NUMBER' + ','
                args  = 'p.set_options(' + args[0:-1] +')'
                
                eval(args)
                print('PUNC: ', punc)
                def process_tw(text):
                    cleaned = p.clean(text).lower()
                    if punc:
                        cleaned = cleaned.translate(str.maketrans('', '', string.punctuation))
                    splitted = cleaned.split()
                    resultwords  = [word for word in splitted if word.lower() not in stopwords]
                    result = ' '.join(resultwords)
                    result = ' ' + result + ' '
                    
                    for arr in corrections:
                        #print('1: ',result)
                        result = result.replace(' '+arr[0]+' ', ' '+arr[1]+' ')
                        #print('2: ', result)
                    cleaned = result

                    twt = TextBlob(cleaned)

                    polarity = 0
                    subjectivity = 0
                    pos = ''
                    noun_phrases = ''

                    if 'polarity' in nlp:
                        polarity = twt.sentiment.polarity
                    
                    if 'subjectivity' in nlp:
                        subjectivity = twt.sentiment.subjectivity
                    
                    if 'pos_tagging' in nlp:
                        pos = twt.tags

                    if 'noun_phrases' in nlp:
                        noun_phrases = twt.noun_phrases

                    
                    
                    return cleaned, proc_name, subjectivity, polarity, str(pos), str(noun_phrases)

                print('corr: ', corrections)
                table["tweet_text"], table['processor_name'], table['subjectivity'], table['polarity'], table['pos'], table['noun_phrases'] = zip(*table.tweet_text.map(process_tw))
                
                print('OK: ', remainder)

                
                table.to_sql('df_tweets_processed', engine, if_exists='append', index=False)

            else:
                print('pass', remainder)
                pass
    engine.dispose()
    


    #p.clean('Preprocessor is #awesome 👍 https://github.com/s/preprocessor')
    


    
    
 
   
    



 
    


    