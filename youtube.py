import os
import requests
from datetime import datetime, timezone

from entry import Entry

API_KEY = os.environ.get('youtube_token', None)

def get_entries(cache, feed_url):
  if 'channel_id' in feed_url: # By channel
    channel_id = feed_url.split('channel_id=')[1]
    if not cache[feed_url].get('title', None):
      cache[feed_url]['title'] = get_title('channels', id=channel_id)['snippet']['title']
    upload_playlist = get_channel_upload_playlist(channel_id)
    videos = get_playlist_items(upload_playlist)
    return get_video_entries(videos)
  elif 'playlist_id' in feed_url: # By playlist
    playlist_id = feed_url.split('playlist_id=')[1]
    if not cache[feed_url].get('title', None):
      cache[feed_url]['title'] = get_title('playlistItems', playlistId=playlist_id)['videoOwnerChannelTitle']
    videos = get_playlist_items(playlist_id)
    return get_video_entries(videos)


def get_channel_upload_playlist(channel_id):
  params = {
    'key': API_KEY,
    'part': 'contentDetails',
    'id': channel_id,
    'maxResults': 50,
  }

  r = requests.get('https://www.googleapis.com/youtube/v3/channels', params=params)
  j = r.json()
  if 'error' in j:
    print(j)
  return j['items'][0]['contentDetails']['relatedPlaylists']['uploads']

def get_playlist_items(playlist_id):
  params = {
    'key': API_KEY,
    'part': 'contentDetails',
    'playlistId': playlist_id,
    'maxResults': 50, # Per page, in playlist order
  }

  r = requests.get('https://www.googleapis.com/youtube/v3/playlistItems', params=params)
  j = r.json()
  if 'error' in j:
    print(j)
  video_ids = [item['contentDetails']['videoId'] for item in j['items']]
  return list(set(video_ids)) # Some playlists may contain dupes, we don't want to send duplicate emails.


def get_video_entries(video_ids):
  params = {
    'key': API_KEY,
    'part': 'id,liveStreamingDetails,snippet',
    'id': ','.join(video_ids),
  }

  r = requests.get('https://www.googleapis.com/youtube/v3/videos', params=params)
  j = r.json()
  if 'error' in j:
    print(j)
  for video in j['items']:
    if 'liveStreamingDetails' in video and 'scheduledStartTime' in video['liveStreamingDetails']:
      start_time = parse_time(video['liveStreamingDetails']['scheduledStartTime'])
      if start_time > datetime.now(timezone.utc):
        print(f'Found YT premier starting in the future, skipping: {start_time} {video["id"]}')
        continue

    entry = Entry()
    entry.title = video['snippet']['title']
    entry.content = video['snippet']['description']
    entry.link = 'https://www.youtube.com/watch?v=' + video['id']
    entry.date = int(parse_time(video['snippet']['publishedAt']).timestamp())

    yield entry


def get_title(api, **params):
  params['key'] = API_KEY
  params['part'] = 'snippet'

  r = requests.get('https://www.googleapis.com/youtube/v3/' + api, params=params)
  j = r.json()
  if 'error' in j:
    print(j)
  return j['items'][0]


def parse_time(string):
  dt = datetime.strptime(string, '%Y-%m-%dT%H:%M:%SZ')
  dt = dt.replace(tzinfo=timezone.utc) # strptime assumes local time, which is incorrect here.
  return dt
