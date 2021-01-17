def Processor(user_name, proc_name, tracker, preproc, stopwords_file, corrections_file):

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

   
    
    for remainder in range(0,10):
        table = pd.read_sql_query("""
            with base as (
                select distinct
                    a.tweet_tweet_id, tweet_text, null as name
                from
                    df_merge a, tracker_tracker b
                where
                    a.query_name = b.query_name 
                  
                    and tweet_text not like 'RT @%'
                    and b.id in ({0})

                union 

                select distinct 
                    tweet_id, text, null as name
                from 
                    df_tweets_referenced_meta a, tracker_tracker b
                where 
                    a.query_name = b.query_name 
           
                    and b.id in ({0})
                )
                select * from base where mod(tweet_tweet_id::bigint,10) = {1}
        """.format(tracker, remainder), engine)

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
        
                return cleaned, proc_name

            print('corr: ', corrections)
            table["tweet_text"], table['processor_name'] = zip(*table.tweet_text.map(process_tw))
            
        

            print('OK: ', remainder)
            table.to_sql('df_tweets_processed', engine, if_exists='append', index=False)
        
        else:
            print('pass', remainder)
            pass

    


    #p.clean('Preprocessor is #awesome 👍 https://github.com/s/preprocessor')
    


    
    
 
   
    



 
    


    