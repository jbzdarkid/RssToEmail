import defusedxml
defusedxml.defuse_stdlib() # For safety around SAXException

import feedparser
from calendar import timegm
from fileinput import input as fileinput
from html import unescape
from traceback import print_exception
from urllib.error import URLError
from xml.sax import SAXException

from entry import Entry


def get_entries(cache, feed_url):
    etag = None
    modified = None
    if cache_data := cache.get(feed_url, None):
        etag = cache_data.get('etag', None)
        modified = cache_data.get('modified', None)

    try:
        d = feedparser.parse(feed_url, etag=etag, modified=modified)
    except ConnectionError as e:
        d = {'status': 500, 'bozo': 1, 'bozo_exception': e, 'entries': []}

    # Update the cache title in case it has changed
    if 'feed' in d and 'title' in d['feed']:
        cache[feed_url]['name'] = d['feed']['title']

    # Bozo may be set to 1 if the feed has an error (but is still parsable). Since I dEon't own these feeds, there's no need to report this.
    if d['bozo'] == 1 and isinstance(d['bozo_exception'], URLError): # Network error
        print(f'URLError while parsing feed: {feed_url}')
        print_exception(None, d['bozo_exception'], None, chain=False)
        return [] # These two errors are indicative of a critical parse failure, so there's no value in continuing.

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
            try:
                entry.date = int(timegm(row['published_parsed']))
            except TypeError:
                print(row)
                raise
        if 'description' in row:
            entry.content = row['description']
        elif 'content' in row:
            entry.content = next(c['value'] for c in row['content'] if c['type'] == 'text/html')
        entries.append(entry)

    return entries
