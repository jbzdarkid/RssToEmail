import json
import os
import random
import requests
from datetime import datetime
from entry import Entry
from time import sleep

# Elon why are there this many required arguments
# Update this by using the inspector in chrome and actually loading someone's timeline. Probably stable per graphql.
features = {
  'articles_preview_enabled': True,
  'c9s_tweet_anatomy_moderator_badge_enabled': True,
  'communities_web_enable_tweet_community_results_fetch': True,
  'creator_subscriptions_quote_tweet_preview_enabled': False,
  'creator_subscriptions_tweet_preview_api_enabled': True,
  'freedom_of_speech_not_reach_fetch_enabled': True,
  'graphql_is_translatable_rweb_tweet_is_translatable_enabled': True,
  'hidden_profile_likes_enabled': False,
  'highlights_tweets_tab_ui_enabled': False,
  'longform_notetweets_consumption_enabled': True,
  'longform_notetweets_inline_media_enabled': True,
  'longform_notetweets_rich_text_read_enabled': True,
  'responsive_web_edit_tweet_api_enabled': True,
  'responsive_web_enhance_cards_enabled': False,
  'responsive_web_graphql_exclude_directive_enabled': True,
  'responsive_web_graphql_skip_user_profile_image_extensions_enabled': False,
  'responsive_web_graphql_timeline_navigation_enabled': True,
  'responsive_web_twitter_article_tweet_consumption_enabled': True,
  'rweb_tipjar_consumption_enabled': True,
  'rweb_video_timestamps_enabled': True,
  'standardized_nudges_misinfo': True,
  'subscriptions_verification_info_verified_since_enabled': False,
  'tweet_awards_web_tipping_enabled': False,
  'tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled': True,
  'tweetypie_unmention_optimization_enabled': True,
  'verified_phone_label_enabled': False,
  'view_counts_everywhere_api_enabled': True,
}

headers = {
  # The public Bearer token used to call guest APIs. Scraped from the twitter service worker:
  # https://abs.twimg.com/responsive-web/client-serviceworker/serviceworker.56c0036a.js (as loaded from https://twitter.com/sw.js)
  'Authorization': 'Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA',
  'User-Agent': 'RssToEmail/0.1 (https://github.com/jbzdarkid/RssToEmail; https://github.com/jbzdarkid/RssToEmail/issues)',
}


def get(graphql, **kwargs):
  """ Guest API access (slow, inconsistent, and doesn't fetch tweets in order)
  if 'x-guest-token' not in headers:
    for _ in range(10):
      r = requests.post('https://api.twitter.com/1.1/guest/activate.json', headers=headers)
      j = r.json()
      if 'guest_token' in j:
        headers['x-guest-token'] = j['guest_token']
        break
      sleep(30)
    if 'x-guest-token' not in headers:
      return None
  """

  # https://stackoverflow.com/a/2782859
  csrf = f'{random.randrange(16**32):032x}'

  cookies = {
    'auth_token': os.environ.get('twitter_token'), # Generate by logging in to twitter and using inspector to get this header.
    'ct0': csrf,
  }
  headers['x-csrf-token'] = csrf

  data = {'features': json.dumps(features), 'variables': json.dumps(kwargs)}
  r = requests.get(f'https://twitter.com/i/api/graphql/{graphql}', data=data, headers=headers, cookies=cookies)
  j = r.json()
  if 'errors' in j:
      raise ValueError(j['errors'])
  return j['data']


def get_user_id(screen_name):
  j = get('oUZZZ8Oddwxs8Cd3iW3UEA/UserByScreenName', screen_name=screen_name)
  if not j:
    raise ValueError('Failed to look up user id')
  return j['user']['result']['rest_id']


def get_entries(user_id):
  kwargs = {
    'userId': user_id,
    'count': 200,
    'includePromotedContent': False,
    'withQuickPromoteEligibilityTweetFields': False,
    'withVoice': False,
    'withV2Timeline': True,
  }
  j = get('V7H0Ap3_Hh2FyS75OCDO3Q/UserTweets', **kwargs)
  if not j:
    return []
  instructions = j['user']['result']['timeline_v2']['timeline']['instructions']
  instructions = {i['type']: i for i in instructions}
  if 'TimelineAddEntries' not in instructions:
    print(f'TimelineAddEntries not found in instruction keys: {instructions.keys()}')
    return []
  tweets = instructions['TimelineAddEntries']['entries']

  entries = []
  for tweet in tweets:
    if tweet['content']['entryType'] != 'TimelineTimelineItem':
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
  user_id = get_user_id('breachwizards')
  print('User id:', user_id)
  entries = get_entries(user_id)
  print(f'Found {len(entries)} entries:')
  entries.sort(key = lambda e: e.date if e.date else 0, reverse=True)
  for e in entries:
    print('-'*50)
    print(e.content)