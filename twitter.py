import requests
import json
from datetime import datetime
from entry import Entry

# Elon why are there this many required arguments
features = {
  'creator_subscriptions_tweet_preview_api_enabled': False,
  'freedom_of_speech_not_reach_fetch_enabled': False,
  'graphql_is_translatable_rweb_tweet_is_translatable_enabled': False,
  'hidden_profile_likes_enabled': False,
  'highlights_tweets_tab_ui_enabled': False,
  'longform_notetweets_consumption_enabled': False,
  'longform_notetweets_inline_media_enabled': False,
  'longform_notetweets_rich_text_read_enabled': False,
  'responsive_web_edit_tweet_api_enabled': False,
  'responsive_web_enhance_cards_enabled': False,
  'responsive_web_graphql_exclude_directive_enabled': False,
  'responsive_web_graphql_skip_user_profile_image_extensions_enabled': False,
  'responsive_web_graphql_timeline_navigation_enabled': False,
  'responsive_web_media_download_video_enabled': False,
  'responsive_web_twitter_article_tweet_consumption_enabled': False,
  'rweb_lists_timeline_redesign_enabled': False,
  'standardized_nudges_misinfo': False,
  'subscriptions_verification_info_verified_since_enabled': False,
  'tweet_awards_web_tipping_enabled': False,
  'tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled': False,
  'tweetypie_unmention_optimization_enabled': False,
  'verified_phone_label_enabled': False,
  'view_counts_everywhere_api_enabled': False,
}

headers = {
  # The public Bearer token used to call guest APIs. Scraped from the twitter service worker:
  # https://abs.twimg.com/responsive-web/client-serviceworker/serviceworker.56c0036a.js (as loaded from https://twitter.com/sw.js)
  'Authorization': 'Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA',
  'User-Agent': 'RssToEmail/0.1 (https://github.com/jbzdarkid/RssToEmail; https://github.com/jbzdarkid/RssToEmail/issues)',
}


def get(graphql, **kwargs):
  if 'x-guest-token' not in headers:
    r = requests.post('https://api.twitter.com/1.1/guest/activate.json', headers=headers)
    headers['x-guest-token'] = r.json()['guest_token']

  data = {'features': json.dumps(features), 'variables': json.dumps(kwargs)}
  r = requests.get(f'https://twitter.com/i/api/graphql/{graphql}', data=data, headers=headers)
  j = r.json()
  if 'errors' in j:
      raise ValueError(j['errors'])
  return j['data']


def get_user_id(screen_name):
  j = get('oUZZZ8Oddwxs8Cd3iW3UEA/UserByScreenName', screen_name=screen_name)
  return j['user']['result']['rest_id']


def get_entries(user_id):
  kwargs = {
    'userId': user_id,
    'includePromotedContent': False,
    'withVoice': False,
  }
  j = get('QqZBEqganhHwmU9QscmIug/UserTweets', **kwargs)
  instructions = j['user']['result']['timeline']['timeline']['instructions']
  instructions = {i['type']: i for i in instructions}
  if 'TimelineAddEntries' not in instructions:
    print(f'TimelineAddEntries not found in instruction keys: {instructions.keys()}')
    return []
  tweets = instructions['TimelineAddEntries']['entries']

  entries = []
  for tweet in tweets:
    if tweet['content']['entryType'] != 'TimelineTimelineItem':
      print('Skipping non-tweet: ' + tweet['content']['entryType'])
      continue
    content = tweet['content']['itemContent']['tweet_results']['result']['legacy']
    user = tweet['content']['itemContent']['tweet_results']['result']['core']['user_results']['result']
    handle = user['legacy']['screen_name']
    tweet_id = content['conversation_id_str'] # Avoids duplicate entries for conversations.

    entry = Entry()
    entry.title = f'@{handle} on Twitter'
    entry.link = f'https://twitter.com/{handle}/status/{tweet_id}'
    entry.date = int(datetime.strptime(content['created_at'], '%a %b %d %H:%M:%S %z %Y').timestamp())
    entry.content = content['full_text']
    entries.append(entry)

  return entries


if __name__ == '__main__':
  user_id = get_user_id('valvesoftware')
  print(get_entries(user_id))