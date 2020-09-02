from smtplib import SMTP
from email.message import EmailMessage
from email.mime.text import MIMEText
import feedparser
from os import environ
from datetime import datetime
from time import mktime
from json import load

def to_datetime(struct_time):
    if struct_time is None:
        return None
    return int(mktime(struct_time))


def parse_feeds(cache, feed_url, email_server):
    d = feedparser.parse(feed_url)
    feed_title = d['feed']['title']

    # Not present for all feeds
    feed_updated = to_datetime(d['feed'].get('published_parsed') or d.get('updated_parsed'))
    if feed_updated < cache['last_updated']:
        return # No need to parse entries if the feed hasn't been updated since then

    if feed_url not in cache:
        cache[feed_url] = {
            'name': feed_title,
            'seen_entries': [],
        }
    else:
        # Potentially update title
        cache[feed_url]['name'] = feed_title

    for entry in d['entries']:
        title = entry['title']
        link = entry['link']
        # Not all entries have a date
        entry_date = to_datetime(entry.get('published_parsed'))
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
                send_email(email_server, title, content)
        else:
            if link not in cache[feed_url]['seen_entries']:
                send_email(email_server, title, content)
                cache[feed_url]['seen_entries'].append(link)


def send_email(email_server, title, content):
    if email_server is None:
        print(title, content)
        return

    msg = EmailMessage()
    msg['Subject'] = title
    msg['To'] = environ['target_email']
    msg['From'] = environ['sender_email']
    msg['Date'] = datetime.today().strftime('%A, %B %d, %Y') 

    msg.attach(MIMEText(content, 'html'))
    email_server.sendmail(msg['From'], msg['To'], msg.as_string())


if __name__ == '__main__':
    with open('entries_cache.json', 'r') as f:
        cache = load(f)

    email_server = SMTP('smtp.gmail.com', 587)
    email_server.ehlo()
    email_server.starttls()
    if 'sender_email' in environ:
        email_server.login(environ['sender_email'], environ['sender_password'])

    with open('feed_list.txt', 'r') as f:
        for feed_url in f:
            if feed_url.startswith('#'):
                continue
            parse_feeds(cache, feed_url, email_server)

    email_server.quit()

    with open('entries_cache.json', 'r') as f:
        dump(cache, j, sort_keys=True, indent=2)

    # Commit changes... ?
