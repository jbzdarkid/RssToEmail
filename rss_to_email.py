import feedparser
from email.message import EmailMessage
from email.mime.text import MIMEText
from json import load, dump
from os import environ
from smtplib import SMTP
from time import mktime, time, strftime, sleep

try:
    SENDER_EMAIL = environ['sender_email']
    SENDER_PWORD = environ['sender_pword']
    TARGET_EMAIL = environ['target_email']
except KeyError:
    SENDER_EMAIL = None
    SENDER_PWORD = None
    TARGET_EMAIL = None


def to_seconds(struct_time):
    if struct_time is None:
        return None
    return int(mktime(struct_time))


def parse_feeds(cache, feed_url, email_server):
    d = feedparser.parse(feed_url)
    feed_title = d['feed']['title']

    # Not present for all feeds
    # feed_updated = to_seconds(d['feed'].get('published_parsed') or d.get('updated_parsed'))
    # if feed_updated < cache['last_updated']:
    #     return # No need to parse entries if the feed hasn't been updated since then

    if feed_url not in cache:
        cache[feed_url] = {
            'name': feed_title,
            'last_updated': 0,
            'seen_entries': [],
        }
    else:
        # Potentially update title
        cache[feed_url]['name'] = feed_title

    for entry in reversed(d['entries']):
        title = entry['title']
        link = entry['link']
        # Not all entries have a date
        entry_date = to_seconds(entry.get('published_parsed'))
        content = None
        if 'content' not in entry:
            content = entry['description']
        else:
            for c in entry['content']:
                if c['type'] == 'text/html':
                    content = c['value']
                    break

        if entry_date:
            if entry_date > cache[feed_url]['last_updated']:
                send_email(email_server, title, entry_date, link, content)
                cache[feed_url]['last_updated'] = entry_date
        else:
            if link not in cache[feed_url]['seen_entries']:
                send_email(email_server, title, None, link, content)
                cache[feed_url]['seen_entries'].append(link)

        with open('entries_cache.json', 'w') as f:
            dump(cache, f, sort_keys=True, indent=2)


def send_email(email_server, title, date, link, content):
    msg = EmailMessage()
    msg['Subject'] = title
    msg['To'] = TARGET_EMAIL
    msg['From'] = 'RSS To Email'
    # msg['Date'] = time()

    msg.set_content('New RSS post: ' + link)
    content += f'<hr>To view the full post, <a href="{link}">click here</a>.'
    if date:
      content += f'<br>This was originally posted at {date}.'
    msg.add_alternative(content, subtype='html')
    email_server.sendmail(SENDER_EMAIL, TARGET_EMAIL, msg.as_string())
    sleep(5) # Avoid spamming emails too hard


if __name__ == '__main__':
    with open('entries_cache.json', 'r') as f:
        cache = load(f)

    email_server = SMTP('smtp.gmail.com', 587)
    email_server.ehlo()
    email_server.starttls()
    if SENDER_EMAIL:
        email_server.login(SENDER_EMAIL, SENDER_PWORD);

    with open('feed_list.txt', 'r') as f:
        for line in f:
            feed_url = line[:line.find('#')].strip()
            if feed_url == '':
              continue
            parse_feeds(cache, feed_url, email_server)

    email_server.quit()

