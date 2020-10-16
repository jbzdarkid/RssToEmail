import feedparser
import sys
from email.message import EmailMessage
from fileinput import input as fileinput
from json import load, dump
from os import environ
from smtplib import SMTP, SMTPException
from time import localtime, mktime, sleep, strftime
from traceback import format_exc, print_exc
from urllib.error import URLError
from xml.sax import SAXException

SENDER_EMAIL = environ.get('sender_email', None)
SENDER_PWORD = environ.get('sender_pword', None)
TARGET_EMAIL = environ.get('target_email', None)
EMAIL_SERVER = environ.get('email_server', None)

def to_seconds(struct_time):
    if struct_time is None:
        return None
    return int(mktime(struct_time))


def parse_feeds(cache, feed_url, email_server):
    etag = None
    if feed_url in cache and 'etag' in cache[feed_url]:
        etag = cache[feed_url]['etag']
    modified = None
    if modified in cache and 'modified' in cache[feed_url]:
        modified = cache[feed_url]['modified']

    d = feedparser.parse(feed_url, etag=etag, modified=modified)

    # Bozo may be set to 1 for recoverable errors. Since I don't own these feeds, there's no need to report this.
    if d['bozo'] == 1:
        if isinstance(d['bozo_exception'], URLError): # Network error
            raise d['bozo_exception']
        if isinstance(d['bozo_exception'], SAXException): # XML parse error
            raise d['bozo_exception']

    if d['status'] == 304: # etag / modified indicates no new data
        return
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
        return

    feed_title = d['feed']['title']

    if feed_url not in cache:
        cache[feed_url] = {
            'name': feed_title,
            'last_updated': 0,
            'seen_entries': [],
        }
    else:
        # Potentially update title
        cache[feed_url]['name'] = feed_title

    if 'etag' in d:
        cache[feed_url]['etag'] = d.etag
    if 'modified' in d:
        cache[feed_url]['modified'] = d.modified

    for entry in reversed(d['entries']):
        title = entry['title']
        link = entry['link']
        # Not all entries have a date
        entry_date = to_seconds(entry.get('published_parsed'))
        content = None
        if 'content' not in entry:
            if 'description' not in entry:
                continue
            content = entry['description']
        else:
            for c in entry['content']:
                if c['type'] == 'text/html':
                    content = c['value']
                    break

        if entry_date:
            if entry_date > cache[feed_url]['last_updated']:
                send_email(email_server, title, feed_title, entry_date, link, content)
                cache[feed_url]['last_updated'] = entry_date
        else:
            if link not in cache[feed_url]['seen_entries']:
                send_email(email_server, title, feed_title, None, link, content)
                cache[feed_url]['seen_entries'].append(link)

        with open('entries_cache.json', 'w') as f:
            dump(cache, f, sort_keys=True, indent=2)


def send_email(email_server, title, feed_title, date, link, content):
    msg = EmailMessage()
    msg['Subject'] = title.replace('\n', '').replace('\r', '')
    msg['To'] = TARGET_EMAIL
    msg['From'] = feed_title

    msg.set_content('New RSS post: ' + link)
    content += f'<hr>To view the full post, <a href="{link}">click here</a>.'
    if date:
      content += f'<br>This was originally posted at {strftime("%A, %B %d, %Y", localtime(date))}.'
    msg.add_alternative(content, subtype='html')
    if SENDER_EMAIL and TARGET_EMAIL:
        email_server.sendmail(SENDER_EMAIL, TARGET_EMAIL, msg.as_string())
        sleep(5) # Avoid hitting throttling limits


if __name__ == '__main__':
    with open('entries_cache.json', 'r') as f:
        cache = load(f)

    print(len(EMAIL_SERVER), len(SENDER_EMAIL), len(SENDER_PWORD))
    email_server = SMTP()
    email_server.connect(EMAIL_SERVER, 587)
    email_server.starttls()
    if SENDER_EMAIL:
        email_server.login(SENDER_EMAIL, SENDER_PWORD);

    success = True
    feeds = []
    with open('feed_list.txt', 'r') as f:
        for line in f:
            feed_url = line[:line.find('#')].strip()
            if feed_url == '':
                continue
            feeds.append(feed_url)

    for feed_url in feeds:
        try:
            parse_feeds(cache, feed_url, email_server)
        except KeyboardInterrupt:
            print_exc()
            success = False
            break
        except SMTPException: # Indicates throttling in the SMTP client
            print_exc()
            success = False
            break
        except Exception:
            print('Exception while parsing feed: ' + feed_url + '\n' + format_exc(chain=False))
            success = False
            continue

    email_server.quit()
    sys.exit(0 if success else 1)

