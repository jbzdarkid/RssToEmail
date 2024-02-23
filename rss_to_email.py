import ssl
import sys
from calendar import timegm
from datetime import datetime, timezone
from fileinput import input as fileinput
from html import unescape
from http.client import responses as http_codes
from json import load, dump
from smtplib import SMTP, SMTPException
from time import time
from traceback import format_exc, print_exc

import generic, youtube, hearthstone, twitter
# from entry import *


# Disable SSL verification, because many of these websites are run by small developers who don't care about https
# https://stackoverflow.com/q/28282797
try:
    ssl._create_default_https_context = ssl._create_unverified_context
except AttributeError:
    pass

success = True
def wrap_generator(feed_title, feed_url, generator):
    global success
    entries = []
    try:
        for entry in generator():
            entries.append(entry)
    except KeyboardInterrupt:
        print_exc()
        success = False
    except Exception:
        print('Exception while parsing feed: ' + feed_url + '\n' + format_exc(chain=False))
        success = False

    # Generators can leave out feed_title if they set the title themselves.
    if feed_title and feed_url not in cache:
        cache[feed_url] = {
            'name': feed_title,
            'last_updated': 0,
            'seen_entries': [],
        }

    for entry in entries: # Small fixup to avoid redundancy. Eh.
        entry.url = feed_url
    return entries


def handle_entries(entries, cache, email_server):
    new_entries = []
    # Reversed so that older entries are first, that way we send emails in chronological order,
    # and send multiple emails if there we multiple entries since the last_updated time.
    for entry in reversed(entries):
        if entry.date:
            if entry.date > cache[entry.url]['last_updated']:
                print(f'Found new entry for {entry.url} by date')
                cache[entry.url]['last_updated'] = entry.date
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

    with open('entries_cache.json', 'w') as f:
        dump(cache, f, sort_keys=True, indent=2)


if __name__ == '__main__':
    with open('entries_cache.json', 'r') as f:
        cache = load(f)

    entries = []

    feeds = []
    twitter_feeds = []
    with open('feed_list.txt', 'r') as f:
        for line in f:
            feed_url = line[:line.find('#')].strip()
            if feed_url == '':
                continue
            elif feed_url == 'stop':
                break
            elif 'youtube' in feed_url:
                youtube_feeds.append(feed_url)
            elif 'twitter' in feed_url:
                twitter_feeds.append(feed_url)
            else:
                feeds.append(feed_url)

    for feed_url in feeds:
        entries += wrap_generator(None, feed_url, lambda: generic.get_entries(cache, feed_url))

    for feed_url in youtube_feeds:
        entries += wrap_generator(None, feed_url, lambda: youtube.get_entries(cache, feed_url))

    for feed_url in twitter_feeds:
        if not feed_url[-1].isdigit(): # Normalize twitter URLs to use IDs, not names.
            old_url = feed_url
            user_id = twitter.get_user_id(feed_url.split('/')[-1])
            feed_url = 'https://twitter.com/i/user/' + user_id
            for line in fileinput('feed_list.txt', inplace=True):
                print(line.replace(old_url, feed_url), end='')

        user_id = feed_url.split('/')[-1]
        entries += wrap_generator('Twitter user ' + user_id, feed_url, lambda user_id=user_id: twitter.get_entries(user_id))

    entries += wrap_generator('Hearthstone Patch Notes', 'hearthstone_patch_notes', lambda: hearthstone.get_entries())

    print(f'Found {len(entries)} entries to process')

    email_server = SMTP(EMAIL_SERVER, 587)
    if SENDER_EMAIL:
        email_server.starttls()
        email_server.login(SENDER_EMAIL, SENDER_PWORD);

    handle_entries(entries, cache, email_server)

    if SENDER_EMAIL:
        email_server.quit()
        
    # If any feeds failed while parsing return nonzero to make the user pay attention
    sys.exit(0 if success else 1)
