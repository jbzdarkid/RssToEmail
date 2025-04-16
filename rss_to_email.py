import ssl
import sys
from fileinput import input as fileinput
from json import load, dump
from smtplib import SMTP_SSL
from time import time
from traceback import format_exc, print_exc

import oauth2, generic, youtube, hearthstone, twitter, soup

# Disable SSL verification, because many of these websites are run by small developers who don't care about https
# https://stackoverflow.com/q/28282797
try:
    ssl._create_default_https_context = ssl._create_unverified_context
except AttributeError:
    pass

cache = None
cache_name = 'entries_cache.json'
success = True

def wrap_generator(feed_title, feed_url, generator):
    global success

    if feed_url not in cache:
        print(f'Found new feed {feed_url} which is not in the cache, adding')
        cache[feed_url] = {
            'name': feed_title,
            'last_updated': int(time()),
            'seen_entries': [],
        }

    entries = []
    try:
        entries = list(generator()) # TODO: We could maybe do a partial update here?
    except KeyboardInterrupt:
        print_exc()
        success = False
    except Exception:
        print('Exception while parsing feed: ' + feed_url + '\n' + format_exc(chain=False))
        success = False

    # Entries should be sorted from newest to oldest.
    entries.sort(key = lambda e: e.date if e.date else 0, reverse=True)
    for entry in entries: # Small fixup to avoid redundancy. Eh.
        entry.url = feed_url
    return entries


def handle_entries(entries, email_server):
    new_entries = []
    # Reversed so that older entries are first, that way we send emails in chronological order,
    # and send multiple emails if there we multiple entries since the last_updated time.
    for entry in reversed(entries):
        if entry.date:
            if entry.date > cache[entry.url]['last_updated']:
                print(f'Found new entry for {entry.url} by date')
                cache[entry.url]['last_updated'] = entry.date
                new_entries.append(entry)
            elif len(new_entries) > 0 and entry.url == new_entries[-1].url and entry.date == cache[entry.url]['last_updated']:
                print(f'Found new entry for {entry.url} by date')
                new_entries.append(entry)
        else:
            cache_key = entry.link.replace('https://', 'http://')
            if cache_key not in cache[entry.url]['seen_entries']:
                print(f'Found new entry for {entry.url} by link')
                # Keep only the most recent 20 (OOTS sends only 10)
                cache[entry.url]['seen_entries'] = cache[entry.url]['seen_entries'][-19:] + [cache_key]
                new_entries.append(entry)

    print(f'Found {len(new_entries)} total new entries, sending emails')

    for entry in new_entries:
        entry.send_email(email_server, cache[entry.url]['name'])

    print('Done sending emails')

    with open(cache_name, 'w') as f:
        dump(cache, f, sort_keys=True, indent=2)

if __name__ == '__main__':
    with open(cache_name, 'r') as f:
        cache = load(f)

    entries = []

    feeds = []
    youtube_feeds = []
    twitter_feeds = []
    soup_feeds = []
    with open('feed_list.txt', 'r') as f:
        for line in f:
            feed_url = line[:line.find('#')].strip()
            if feed_url == '':
                continue
            elif feed_url == 'stop':
                break
            elif feed_url.startswith('bs4'):
                soup_feeds.append(feed_url)
            elif 'youtube' in feed_url:
                youtube_feeds.append(feed_url)
            elif 'twitter' in feed_url:
                twitter_feeds.append(feed_url)
            else:
                feeds.append(feed_url)

    for feed_url in feeds:
        entries += wrap_generator(None, feed_url, lambda feed_url=feed_url: generic.get_entries(cache, feed_url))

    for feed_url in youtube_feeds:
        entries += wrap_generator(None, feed_url, lambda feed_url=feed_url: youtube.get_entries(cache, feed_url))

    for feed_url in twitter_feeds:
        if not feed_url[-1].isdigit(): # Normalize twitter URLs to use IDs, not handles, to save an API call.
            old_url = feed_url
            user_id = twitter.get_user_id(feed_url.split('/')[-1])
            feed_url = 'https://twitter.com/intent/user?user_id=' + user_id
            for line in fileinput('feed_list.txt', inplace=True):
                print(line.replace(old_url, feed_url), end='')
        else:
            user_id = feed_url.split('?user_id=')[-1]
        last_update = cache[feed_url]['last_updated']
        entries += wrap_generator('Twitter user ' + user_id, feed_url, lambda user_id=user_id: twitter.get_entries(user_id, last_update))

    for feed_url in soup_feeds:
        entries += wrap_generator(None, feed_url, lambda feed_url=feed_url: soup.get_entries(cache, feed_url))

    # The hearthstone patch notes are actually fetched live, as javascript. As a result, traditional scrapers don't work.
    entries += wrap_generator('Hearthstone Patch Notes', 'hearthstone_patch_notes', lambda: hearthstone.get_entries())

    print(f'Found {len(entries)} entries to process')

    with oauth2.EmailServer() as email_server:
      handle_entries(entries, email_server)

    # If any feeds failed while parsing return nonzero to make the user pay attention
    sys.exit(0 if success else 1)
