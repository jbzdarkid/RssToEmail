feeds = []
with open('feed_list.txt', 'r') as f:
    lines = f.read().split('\n')
    for i in range(0, len(lines)-1, 2):
        feed_name = lines[i]
        feed_url = lines[i+1]

        sortkey = feed_url.split('://')[1]
        if sortkey.startswith('www.'):
            sortkey = sortkey[4:]
        feeds.append((sortkey, feed_name, feed_url))

feeds.sort()

with open('feed_list.txt', 'w', encoding='utf-8') as f:
    for _, feed_name, feed_url in feeds:
        f.write(feed_name + '\n')
        f.write(feed_url + '\n')
