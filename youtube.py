import os
import requests
from datetime import datetime, timezone

from entry import Entry

API_KEY = os.environ['youtube_token']

def get_entries(cache, feed_url):
  if 'channel_id' in feed_url: # By channel
    channel_id = feed_url.split('channel_id=')[1]
    upload_playlist = get_channel_upload_playlist(channel_id)
    videos = get_playlist_items(upload_playlist)
    return get_video_entries(videos)
  elif 'playlist_id' in feed_url: # By playlist
    playlist_id = feed_url.split('playlist_id=')[1]
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
  return [item['contentDetails']['videoId'] for item in j['items']]


def get_video_entries(video_ids):
  params = {
    'key': API_KEY,
    'part': 'id,liveStreamingDetails,snippet',
    'id': ','.join(video_ids),
  }

  r = requests.get('https://www.googleapis.com/youtube/v3/videos', params=params)
  j = r.json()
  for video in j['items']:
    if 'liveStreamingDetails' in video:
      start_time = datetime.strptime(video['liveStreamingDetails']['scheduledStartTime'], '%Y-%m-%dT%H:%M:%SZ')
      if start_time > datetime.now():
        print(f'Found YT premier starting in the future, skipping: {start_time} {video["id"]}')
        continue

    entry = Entry()
    entry.title = video['snippet']['title']
    entry.content = video['snippet']['description']
    entry.link = 'https://www.youtube.com/watch?v=' + video['id']
    published_at = datetime.strptime(video['snippet']['publishedAt'], '%Y-%m-%dT%H:%M:%SZ')
    entry.date = int(published_at.timestamp())

    yield entry
