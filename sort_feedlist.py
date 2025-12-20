from pathlib import Path
import json

feed_list = Path('feed_list.txt')
entries_cache = Path('entries_cache.json')

with entries_cache.open('r', encoding='utf-8') as f:
    entries_cache_json = json.load(f)

    for feed_url in list(entries_cache_json.keys()):
      data = entries_cache_json[feed_url]

feeds = []
with feed_list.open('r', encoding='utf-8') as f:
    lines = f.read().split('\n')
    for i in range(0, len(lines)-1, 2):
        feed_name = lines[i][2:]
        feed_url = lines[i+1]

        if feed_url not in entries_cache_json:
          print(f'Found newly-added feed {feed_name}: {feed_url}, adding to the cache')
          entries_cache_json[feed_url] = {
            'name': feed_name,
            'last_updated': 0,
            'seen_entries': [],
          }
          continue

        if 'title' in data:
          data.pop('title')
        data['name'] = feed_name

        sortkey = feed_url.split('://')[-1]
        if sortkey.startswith('www.'):
            sortkey = sortkey[4:]
        feeds.append((sortkey, feed_name, feed_url))

feeds.sort()

with entries_cache.open('w', encoding='utf-8') as f:
    json.dump(entries_cache_json, f, sort_keys=True, indent=2)

with feed_list.open('w', encoding='utf-8') as f:
    for _, feed_name, feed_url in feeds:
        f.write(feed_name + '\n')
        f.write(feed_url + '\n')
