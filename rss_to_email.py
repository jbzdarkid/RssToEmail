import defusedxml
defusedxml.defuse_stdlib()

import feedparser
import sys
from fileinput import input as fileinput
from html import unescape
from json import load, dump
from smtplib import SMTP, SMTPException
from time import mktime
from traceback import format_exc, print_exc, print_exception
from urllib import request
from urllib.error import URLError
from xml.sax import SAXException

from entry import *

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
            'last_updated': 0,
            'seen_entries': [],
        }

    # Bozo may be set to 1 if the feed has an error (but is still parsable). Since I don't own these feeds, there's no need to report this.
    if d['bozo'] == 1:
        if (isinstance(d['bozo_exception'], URLError) # Network error
         or isinstance(d['bozo_exception'], SAXException)): # XML Parsing error
            print(f'URLError while parsing feed: {feed_url}\n')
            print_exception(d['bozo_exception'], None, None, chain=False)
            return [] # These two errors are indicative of a critical parse failure, so there's no value in continuing.

    if d['status'] == 304: # etag / modified indicates no new data
        return []
    if d['status'] == 301:
        print(f'Feed {feed_url} has permanently moved to {d.href}')
        for line in fileinput('feed_list.txt', inplace=True):
            print(line.replace(feed_url, d.href), end='')
        cache[d.href] = cache[feed_url]
        del cache[feed_url]
        feed_url = d.href
    if d['status'] == 410:
        print(f'Feed {feed_url} has been permanently deleted')
        for line in fileinput('feed_list.txt', inplace=True):
            if feed_url not in line:
                print(line, end='')
                continue

            print('# (Permanently deleted)')
            print('# ' + line, end='')
        return []

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
    new_entries = 0
    # Reversed so that older entries are first, that way we send emails in chronological order.
    for entry in reversed(entries):
        if entry.date:
            if entry.date > cache[entry.url]['last_updated']:
                print(f'Found new entry for {entry.url} by date')
                entry.send_email(email_server, cache[entry.url]['name'])
                new_entries += 1

                cache[entry.url]['last_updated'] = entry.date
                with open('entries_cache.json', 'w') as f:
                    dump(cache, f, sort_keys=True, indent=2)
        else:
            if entry.link not in cache[entry.url]['seen_entries']:
                print(f'Found new entry for {entry.url} by link')
                entry.send_email(email_server, cache[entry.url]['name'])
                new_entries += 1

                cache[entry.url]['seen_entries'].append(entry.link)
                # Keep only the most recent 20 (OOTS sends only 10)
                cache[entry.url]['seen_entries'] = cache[entry.url]['seen_entries'][-20:]

                with open('entries_cache.json', 'w') as f:
                    dump(cache, f, sort_keys=True, indent=2)

    print(f'Found {new_entries} total new entries')


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
            if 'deviantart' in feed_url:
                continue # DeviantArt RSS is broken right now.
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

    print(f'Found {len(entries)} entries')

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

