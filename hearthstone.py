from urllib import request
from json import load
from entry import Entry

def get_entries():
    feed_url = 'https://playhearthstone.com/en-us/api/blog/articleList/?page=1&pageSize=10&tagsList[]=patch'
    data = load(request.urlopen(feed_url))

    for row in data:
        entry = Entry()
        entry.title = row['title']
        entry.link = row['defaultUrl']
        entry.date = row['created'] // 1000
        entry.url = feed_url
        entry.content = row['content']
        yield entry
