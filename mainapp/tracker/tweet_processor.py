import pandas as pd
def get_place_info(includes):
    places = []
    for place in includes.get('places',''):
        full_name = place.get('full_name','')
        id_ = place.get('id','')
        country = place.get('country','')
        country_code = place.get('country_code','')
        name = place.get('name','')
        place_type = place.get('place_type','')
        places.append([full_name, id_, country, country_code, name, place_type])
    place_df = pd.DataFrame(places, columns = ['place_full_name', 'id', 'country', 'country_code', 'place_name', 'place_type'])         
    return place_df

def get_simple_tweet_info(data):
    tweets = []
    for tweet in data:
        tweet_id = tweet.get('id','')
        text = tweet.get('text','')
        author_id = tweet.get('author_id','')
        created_at = tweet.get('created_at','')
        lang = tweet.get('lang','')
        conversation_id = tweet.get('conversation_id','')
        possibly_sensitive = tweet.get('possibly_sensitive','')
        in_reply_to_user_id = tweet.get('in_reply_to_user_id','')
        source = tweet.get('source','')

        retweet_count = ''
        reply_count = ''
        like_count = ''
        quote_count = ''
        if tweet.get('public_metrics',''):
            retweet_count = tweet['public_metrics'].get('retweet_count','')
            reply_count = tweet['public_metrics'].get('reply_count','')
            like_count = tweet['public_metrics'].get('like_count','')
            quote_count = tweet['public_metrics'].get('quote_count','')

        withheld = ''
        if tweet.get('withheld',''):    
            withheld = tweet['withheld'].get('copyright','')

        coordinate = ''
        place_id = ''
        if tweet.get('geo',''):
            if tweet['geo'].get('coordinates',''):
                coordinate = tweet['geo']['coordinates']
            place_id = tweet['geo'].get('place_id','')
            
        
        tweets.append([tweet_id, text, author_id, created_at, lang, conversation_id, possibly_sensitive, 
                       in_reply_to_user_id, source, retweet_count, reply_count, like_count, 
                       quote_count, withheld, coordinate, 
                       place_id])
        
    tweet_df = pd.DataFrame(tweets, columns=['tweet_id', 'text', 'author_id', 'created_at', 'lang', 'conversation_id', 
                                      'possibly_sensitive', 'in_reply_to_user_id', 'source', 'retweet_count', 
                                      'reply_count', 'like_count', 'quote_count', 'withheld', 'coordinate', 
                                      'place_id'])
                                             
    return tweet_df
        
def get_user_info(include):
    users = []
    for user in include['users']:
        user_created_at = user.get('created_at','')
        description = user.get('description','')
        id_ = user.get('id','')
        location = user.get('location','')
        name = user.get('name','')
        protected = user.get('protected','')
        url = user.get('url','')
        username = user.get('username','')
        verified = user.get('verified','')

        try:
            followers_count = user['public_metrics']['followers_count']
        except:
            followers_count = ''
        try:
            following_count = user['public_metrics']['following_count']
        except:
            following_count = ''
        try:
            tweet_count = user['public_metrics']['tweet_count']
        except:
            tweet_count = ''
        try:
            listed_count = user['public_metrics']['listed_count']
        except:
            listed_count = ''

        users.append([id_, username, user_created_at, description, 
                        location, name, protected, url, verified,
                        followers_count, following_count, 
                        tweet_count, listed_count]
                    )
    user_df = pd.DataFrame(users, 
                           columns = ['id', 'username', 'created_at', 'description', 
                                        'location', 'name', 'protected', 'url', 'verified',
                                        'followers_count', 'following_count', 
                                        'tweet_count', 'listed_count']
                          )
    return user_df
                           

def get_media_info(data, includes):
    attachments_meta = []
    if includes.get('media', ''):
        for media in includes['media']:
            media_key =  media.get('media_key','')
            type_ =  media.get('type','')
            url =  media.get('url','')
            if media.get('public_metrics',''):
                view_count =  media.get('public_metrics','').get('view_count', '')
            else:
                view_count = ''
            duration_ms = media.get('duration_ms','')
            attachments_meta.append([media_key, type_, url, view_count, duration_ms])

    if includes.get('polls', ''):
        for poll in includes['polls']:
            poll_key =  poll.get('id','')
            poll_option = poll.get('options', '')
            attachments_meta.append([poll_key, 'poll', str(poll_option), '', ''])


    attachments = []    
    for tweet in data:
        att = tweet.get('attachments','')
        if att:
            for key in att.keys():
                for item in att[key]:
                    attachments.append([tweet['id'],key, item])

    attachments_meta_df = pd.DataFrame(attachments_meta, columns = ['media_key','type', 'url',
                                                                 'view_count', 'duration_ms'])

    attachments_df = pd.DataFrame(attachments, columns = ['tweet_id','category', 'media_key'])


    media_df = pd.merge(attachments_df, attachments_meta_df, on='media_key')
    return media_df

def get_context_annotations(data):
    rows = []
    domain = []
    entity = []
    for entry in data:
        att = entry.get('context_annotations','')
        if att:
            for elem in att:
                try:
                    domain_id = elem['domain']['id']
                except:
                    domain_id = ''
                try:
                    domain_name = elem['domain']['name'] 
                except:
                    domain_name = ''
                try:
                    domain_desc = elem['domain']['description']
                except:
                    domain_desc = ''
                try:
                    entity_id = elem['entity']['id']
                except:
                    entity_id = ''
                try:
                    entity_name = elem['entity']['name'] 
                except:
                    entity_name = ''
                try:
                    entity_desc = elem['entity']['description']
                except:
                    entity_desc = ''


                rows.append([entry['id'],domain_id,entity_id])
                domain.append([domain_id,domain_name,domain_desc])
                entity.append([entity_id,entity_name,entity_desc])
                
    context_df = pd.DataFrame(rows, columns = ['tweet_id', 'domain_id', 'entity_id'])
    domain_lookup_df = pd.DataFrame([list(x) for x in set(tuple(x) for x in domain)], 
                                    columns = ['domain_id', 'domain_name', 'domain_desc'])
    entity_lookup_df = pd.DataFrame([list(x) for x in set(tuple(x) for x in entity)],
                                    columns = ['entity_id', 'entity_name', 'entity_desc'])
    
    return context_df, domain_lookup_df, entity_lookup_df
  

def get_entity_info(data):
    rows = []
    for entry in data:
        att = entry.get('entities','')
        if att:
            for key in att.keys():
                for elem in att.get(key):
                    try:
                        start = elem['start']
                    except:
                        start = ''
                    try:
                        end = elem['end']
                    except:
                        end = ''
                    try:
                        probability = elem['probability']
                    except:
                        probability = ''
                    try:
                        type_of = elem['type']
                    except:
                        type_of = ''
                    try:
                        normalized_text = elem['normalized_text']
                    except:
                        normalized_text = ''
                    try:
                        username = elem['username']
                    except:
                        username = ''                        
                    try:
                        tag = elem['tag']
                    except:
                        tag = ''
                    try:
                        url = elem['url']
                    except:
                        url = ''
                    try:
                        expanded_url = elem['expanded_url']
                    except:
                        expanded_url = ''
                    try:
                        display_url = elem['display_url']
                    except:
                        display_url = ''
                    try:
                        url_title = elem['title']
                    except:
                        url_title = ''
                    try:
                        url_description = elem['description']
                    except:
                        url_description = ''

                    rows.append([entry['id'], key, start, end, probability, type_of, 
                                 username, normalized_text, tag, url, expanded_url, display_url, 
                                 url_title, url_description])

    entity_df = pd.DataFrame(rows, 
                             columns = ['tweet_id', 'category', 'start', 'end', 'probability',
                                                     'type_of', 'username', 'normalized_text', 'tag', 'url',
                                                     'expanded_url', 'display_url', 'url_title',
                                                     'url_description'])
    return entity_df
        
def get_referenced_tweets(data):
    rows = []
    for entry in data:
        att = entry.get('referenced_tweets','')
        for elem in att:
            try:
                _type = elem['type']
            except:
                _type = ''
            try:
                _id = elem['id']
            except:
                _id = ''

            rows.append([entry['id'], _type, _id])
    reference_df = pd.DataFrame(rows, columns = ['tweet_id','type','reference_id'])
    return reference_df

        
def get_all_info(data, includes):
    rows = []
    
    places = get_place_info(includes)
    users = get_user_info(includes)
    tweets = get_simple_tweet_info(data)
    
    tweets_referenced = get_referenced_tweets(data)
    if includes.get('tweets',''):
        tweets_referenced_meta = get_simple_tweet_info(includes['tweets'])
                            
    merged = pd.merge(tweets.add_prefix('tweet_'),
                      places.add_prefix('place_'),
                      how='left',
                      left_on=['tweet_place_id'],right_on=['place_id'])
  
                       
    
    media = get_media_info(data,includes)
    annotations = get_context_annotations(data)
    entities = get_entity_info(data)
    
    return merged, users, tweets_referenced, tweets_referenced_meta, media, annotations, entities