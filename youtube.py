import generic
from urllib import request

def get_entries(cache, feed_url):
    # Special handling to discard youtube premiers, otherwise identical to the generic RSS handler
    for entry in generic.get_entries(cache, feed_url):
        data = request.urlopen(entry.link).read().decode('utf-8', errors='surrogateescape')

        # "Live Broadcast" means premier
        if '<meta itemprop="isLiveBroadcast" content="True">' in data:
            start_date_idx = data.find('<meta itemprop="startDate" content="')
            if start_date_idx == -1:
                continue
            start_date_str = data[start_date_idx+36:start_date_idx+36+25]
            start_date = datetime.strptime(start_date_str, '%Y-%m-%dT%H:%M:%S%z')

            if start_date > datetime.now(timezone.utc):
                continue

    # Not a youtube premier or the premier has released
    yield entry
