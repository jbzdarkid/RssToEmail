import feedparser
from json import load, dump

def get_feed_name(feed_url):
    d = feedparser.parse(feed_url)
    return d['feed'].get('title', None)

feeds = []
with open('feed_list.txt', 'r') as f:
    for line in f:
        feed = line[:line.find('#')].strip()
        if feed == '':
            continue
        if feed.startswith('http://'):
            feed = feed.replace('http', 'https', 1)
        sortkey = feed[8:]
        if sortkey.startswith('www.'):
            sortkey = sortkey[4:]
        feeds.append((sortkey, feed))
feeds.sort()
with open('feed_list.txt', 'w', encoding='utf-8') as f:
    for feed in feeds:
        feed_name = get_feed_name(feed[1])
        if feed_name:
            f.write('# ' + get_feed_name(feed[1]) + '\n')
        f.write(feed[1] + '\n')
