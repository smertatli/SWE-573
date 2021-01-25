import requests
import os
import json

#bearer='AAAAAAAAAAAAAAAAAAAAACx%2BKgEAAAAAFIRKak2afKG3OdcUZpviO3QdBjw%3DKzQ3bV7zSkjqi4guru0bXWtyfld7nKKhK7PUkIjbuiYRmiy7w8'
bearer='AAAAAAAAAAAAAAAAAAAAAKNwMAEAAAAAobPsHsN28XOPVEwcu4PRk5v%2B%2BFo%3DtN3ZG13c0GVGHFDrqsNb87ITHgzZoijNTwr69pqfRF3k43owp8'
def auth():
    return bearer


def create_url(query, fetch_size):
    #"(covid19 OR covid) lang:en"
    print('aosdkaosdkaoskdaoskdoaksdoasd: ', fetch_size)
    media_fields = 'media.fields=media_key,preview_image_url,type,url,public_metrics'
    place_fields = 'place.fields=country,country_code,full_name,geo,id,name,place_type'
    poll_fields  = 'poll.fields=duration_minutes,end_datetime,id,options,voting_status'
    user_fields  = 'user.fields=created_at,description,location,protected,public_metrics,verified,withheld'
    tweet_fields = 'tweet.fields=author_id,created_at,conversation_id,referenced_tweets,attachments,geo,context_annotations,entities,withheld,public_metrics,possibly_sensitive,lang,source'
    expansions   = 'expansions=attachments.poll_ids,attachments.media_keys,author_id,entities.mentions.username,geo.place_id,in_reply_to_user_id,referenced_tweets.id,referenced_tweets.id.author_id'
    url = "https://api.twitter.com/2/tweets/search/recent?query={}&{}&{}&{}&{}&{}&{}&max_results={}".format(
        query, 
        tweet_fields,
        user_fields,
        media_fields,
        place_fields,
        poll_fields,
        expansions,
        fetch_size
    )
    return url


def create_headers(bearer_token):
    headers = {"Authorization": "Bearer {}".format(bearer_token)}
    return headers


def connect_to_endpoint(url, headers):
    response = requests.request("GET", url, headers=headers)
   
    if response.status_code != 200:
        raise Exception(response.status_code, response.text)
    return response.json()


def gettw(query, fetch_size):
    bearer_token = auth()
    url = create_url(query, fetch_size)
    headers = create_headers(bearer_token)
    return connect_to_endpoint(url, headers)
    #print(json.dumps(json_response, indent=4, sort_keys=True))

