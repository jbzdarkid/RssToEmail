import defusedxml
defusedxml.defuse_stdlib()

import feedparser
import ssl
import sys
from datetime import datetime, timezone
from fileinput import input as fileinput
from html import unescape
from http.client import responses as http_codes
from json import load, dump
from smtplib import SMTP, SMTPException
from time import mktime, time
from traceback import format_exc, print_exc, print_exception
from urllib import request
from urllib.error import URLError
from xml.sax import SAXException

from entry import *


# Disable SSL verification, because many of these websites are run by small developers who don't care about https
# https://stackoverflow.com/q/28282797
try:
    ssl._create_default_https_context = ssl._create_unverified_context
except AttributeError:
    pass


def parse_feeds(cache, feed_url):
    etag = None
    modified = None
    if cache_data := cache.get(feed_url, None):
        etag = cache_data.get('etag', None)
        modified = cache_data.get('modified', None)

    d = feedparser.parse(feed_url, etag=etag, modified=modified)

    # In the future, this probably moves out into main scope. Or something.
    if feed_url not in cache:
        cache[feed_url] = {
            'name': d['feed']['title'],
            'last_updated': int(time()),
            'seen_entries': [],
        }

    if d['status'] == 304: # etag / modified indicates no new data
        return []
    elif d['status'] == 301:
        print(f'Feed {feed_url} has permanently moved to {d.href}')
        for line in fileinput('feed_list.txt', inplace=True):
            print(line.replace(feed_url, d.href), end='')
        cache[d.href] = cache[feed_url]
        del cache[feed_url]
        feed_url = d.href
    elif d['status'] in (410, 404):
        print(f'Feed {feed_url} has been deleted')
        code = d['status']
        for line in fileinput('feed_list.txt', inplace=True):
            if feed_url not in line:
                print(line, end='')
                continue

            print(f'# {code} {http_codes[code].upper()}')
            print('# ' + line, end='')
        return []

    # Bozo may be set to 1 if the feed has an error (but is still parsable). Since I don't own these feeds, there's no need to report this.
    if d['bozo'] == 1:
        if (isinstance(d['bozo_exception'], URLError) # Network error
         or isinstance(d['bozo_exception'], SAXException)): # XML Parsing error
            print(f'URLError while parsing feed: {feed_url}')
            print_exception(None, d['bozo_exception'], None, chain=False)
            return [] # These two errors are indicative of a critical parse failure, so there's no value in continuing.


    if 'etag' in d:
        cache[feed_url]['etag'] = d.etag
    if 'modified' in d:
        cache[feed_url]['modified'] = d.modified

    entries = []
    for row in d['entries']:
        entry = Entry()
        entry.title = unescape(row.get('title', '(no title)'))
        entry.link = row['link']
        entry.url = feed_url
        if 'published_parsed' in row: # Not all entries have a date
            entry.date = int(mktime(row['published_parsed']))
        if 'description' in row:
            entry.content = row['description']
        elif 'content' in row:
            entry.content = next(c['value'] for c in row['content'] if c['type'] == 'text/html')
        entries.append(entry)

    return entries


def get_hearthstone_patch_notes():
    feed_url = 'https://playhearthstone.com/en-us/api/blog/articleList/?page=1&pageSize=10&tagsList[]=patch'
    data = load(request.urlopen(feed_url))
    if feed_url not in cache:
        cache[feed_url] = {
            'name': 'Hearthstone Patch Notes',
            'last_updated': 0,
            'seen_entries': [],
        }

    entries = []
    for row in data:
        entry = Entry()
        entry.title = row['title']
        entry.link = row['defaultUrl']
        entry.url = feed_url
        entry.date = row['created'] // 1000
        entry.content = row['content']
        entries.append(entry)

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
        elif entry.link not in cache[entry.url]['seen_entries']:
            print(f'Found new entry for {entry.url} by link')
            # Keep only the most recent 20 (OOTS sends only 10)
            cache[entry.url]['seen_entries'] = cache[entry.url]['seen_entries'][-19:] + [entry.link]
            new_entries.append(entry)

    # Special handling to discard youtube premiers
    def is_valid_entry(entry):
        if 'youtube.com' in entry.url:
            data = request.urlopen(entry.link).read().decode('utf-8', errors='surrogateescape')

            # "Live Broadcast" means premier
            if '<meta itemprop="isLiveBroadcast" content="True">' in data:
                start_date_idx = data.find('<meta itemprop="startDate" content="')
                if start_date_idx == -1:
                    return False
                start_date_str = data[start_date_idx+36:start_date_idx+36+25]
                start_date = datetime.strptime(start_date_str, '%Y-%m-%dT%H:%M:%S%z')

                return start_date <= datetime.now(timezone.utc)

        # Not from youtube, not a youtube premier
        return True


    new_entries[:] = [entry for entry in new_entries if is_valid_entry(entry)]

    print(f'Found {len(new_entries)} total new entries, sending emails')

    for entry in new_entries:
        entry.send_email(email_server, cache[entry.url]['name'])

    print('Done sending emails')

    with open('entries_cache.json', 'w') as f:
        dump(cache, f, sort_keys=True, indent=2)


if __name__ == '__main__':
    with open('entries_cache.json', 'r') as f:
        cache = load(f)

    success = True
    entries = []

    feeds = []
    with open('feed_list.txt', 'r') as f:
        for line in f:
            feed_url = line[:line.find('#')].strip()
            if feed_url == '':
                continue
            elif 'deviantart' in feed_url and datetime.now() < datetime(2021, 8, 1):
                continue # DeviantArt RSS is broken right now. Disable until Oct 1.
            else:
                feeds.append(feed_url)

    for feed_url in feeds:
        try:
            entries += parse_feeds(cache, feed_url)
        except KeyboardInterrupt:
            print_exc()
            success = False
            break
        except Exception:
            print('Exception while parsing feed: ' + feed_url + '\n' + format_exc(chain=False))
            success = False
            continue

    entries += get_hearthstone_patch_notes()

    print(f'Found {len(entries)} entries to process')

    email_server = SMTP(EMAIL_SERVER, 587)
    if SENDER_EMAIL:
        email_server.starttls()
        email_server.login(SENDER_EMAIL, SENDER_PWORD);

    try:
        handle_entries(entries, cache, email_server)
    except SMTPException: # Indicates throttling in the SMTP client
        print_exc()
        success = False
    except KeyboardInterrupt:
        print_exc()
        success = False
    except Exception:
        print('Exception while parsing feed: ' + feed_url + '\n' + format_exc(chain=False))
        success = False


    if SENDER_EMAIL:
        email_server.quit()
    sys.exit(0 if success else 1)

