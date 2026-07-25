import os
import requests
from datetime import datetime, timezone

from entry import Entry

API_KEY = os.environ.get('youtube_token', None)

def make_get_request(path, params):
  try:
    r = requests.get(f'https://www.googleapis.com/youtube/v3/{path}', params=params)
  except requests.exceptions.ConnectionError as e:
    print(e)
    return None
  if r.status_code in [500]:
    return None
  r.raise_for_status()
  j = r.json()
  if 'error' in j:
    print(j)
  return j

def get_entries(cache, feed_url):
  if 'channel_id' in feed_url: # By channel (deprecated)
    channel_id = feed_url.split('channel_id=')[1]
    upload_playlist = get_channel_upload_playlist(channel_id)

    # See https://stackoverflow.com/a/76602819 for more details.
    raise ValueError(f''' \
Please use the direct playlist feed: ?playlist_id={upload_playlist}
To exclude youtube shorts and livestreams, use ?playlist_id=UULF{upload_playlist[2:]}
''')

  elif 'playlist_id' in feed_url: # By playlist
    playlist_id = feed_url.split('playlist_id=')[1]
    videos = get_playlist_items(playlist_id)
    return get_video_entries(videos)
  else:
    raise ValueError(f'Not sure how to get entries from feed url: {feed_url}')


def get_channel_upload_playlist(channel_id):
  # https://stackoverflow.com/a/76602819/2105321
  # I might not need this? What does this come up with...
  params = {
    'key': API_KEY,
    'part': 'contentDetails',
    'id': channel_id,
    'maxResults': 50,
  }

  j = make_get_request('channels', params=params)
  if not j:
    return []
  return j['items'][0]['contentDetails']['relatedPlaylists']['uploads']


def get_playlist_items(playlist_id):
  params = {
    'key': API_KEY,
    'part': 'contentDetails',
    'playlistId': playlist_id,
    'maxResults': 50, # Per page, in playlist order
  }

  j = make_get_request('playlistItems', params=params)
  if not j:
    return []
  video_ids = [item['contentDetails']['videoId'] for item in j['items']]
  return list(set(video_ids)) # Some playlists may contain dupes, we don't want to send duplicate emails.


def get_video_entries(video_ids):
  params = {
    'key': API_KEY,
    'part': 'id,liveStreamingDetails,snippet',
    'id': ','.join(video_ids),
  }

  j = make_get_request('videos', params=params)
  if not j:
    return
  for video in j['items']:
    if 'liveStreamingDetails' in video and 'scheduledStartTime' in video['liveStreamingDetails']:
      start_time = datetime.fromisoformat(video['liveStreamingDetails']['scheduledStartTime'])
      if start_time > datetime.now(timezone.utc):
        print(f'Found YT premier starting in the future, skipping: {start_time} {video["id"]}')
        continue

    entry = Entry()
    entry.title = video['snippet']['title']
    entry.content = video['snippet']['description']
    entry.link = 'https://www.youtube.com/watch?v=' + video['id']
    date_str = video['snippet']['publishedAt']
    entry.date = int(datetime.fromisoformat(date_str).timestamp())

    yield entry


if __name__ == '__main__':
  from collections import defaultdict

  feed_url = 'https://www.youtube.com/feeds/videos.xml?playlist_id=UULF8CX0LD98EDXl4UYX1MDCXg'
  feed_url = 'https://www.youtube.com/feeds/videos.xml?channel_id=UC8CX0LD98EDXl4UYX1MDCXg'
  # feed_url = 'https://www.youtube.com/feeds/videos.xml?channel_id=UC8CX0LD98EDXl4UYX1MDCXg'

  cache = defaultdict(dict)
  for entry in get_entries(cache, feed_url):
    print(entry, entry.title)

  print(cache)
