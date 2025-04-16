import re
from datetime import datetime
from urllib.parse import urljoin

import bs4
import requests

from entry import Entry


headers = {
  'User-Agent': 'RssToEmail/0.3 (https://github.com/jbzdarkid/RssToEmail; https://github.com/jbzdarkid/RssToEmail/issues)',
}

def get_soup(url):
  r = requests.get(url, headers=headers)
  r.raise_for_status()
  soup = bs4.BeautifulSoup(r.text, 'html.parser')

  # Scrape and replace all relative links
  for link in soup.find_all('a', href=True):
    link['href'] = urljoin(r.url, link['href'])
  for img in soup.find_all('img', src=True):
    img['src'] = urljoin(r.url, img['src'])

  return soup


def get_entries(cache, feed_url):
  generator = None
  if feed_url == 'bs4|valorant':
    generator = get_valorant_entries
  elif feed_url == 'bs4|microsoft':
    generator = get_microsoft_sus_entries
  elif feed_url == 'bs4|jollyjack':
    generator = get_sequential_art
  elif feed_url == 'bs4|nerfnow':
    generator = get_nerf_now

  found_any = False
  for entry in generator(cache, feed_url):
    found_any = True
    yield entry

  if not found_any:
    raise ValueError(f'bs4 generator {feed_url} could not find any entries')


# How to create CSS .select filters: https://www.crummy.com/software/BeautifulSoup/bs4/doc/#css-selectors

def get_valorant_entries(cache, feed_url):
  soup = get_soup('https://playvalorant.com/en-us/news/tags/patch-notes')
  cache[feed_url]['name'] = soup.find('title').text
  
  for item in soup.select('a[role="button"]'):
    entry = Entry()
    entry.title = item.select_one('div[data-testid="card-title"]').text
    entry.content = item.select_one('div[data-testid="rich-text-html"] > div').text
    entry.link = item['href']
    date_str = item.select_one('div[data-testid="card-date"] > time')['datetime']
    entry.date = int(datetime.fromisoformat(date_str).timestamp())

    yield entry

def get_microsoft_sus_entries(cache, feed_url):
  soup = get_soup('https://www.microsoft.com/en-us/corporate-responsibility/sustainability/report')
  cache[feed_url]['name'] = soup.find('title').text

  for item in soup.select('div[class~="material-card"]'):
    entry = Entry()
    entry.title = item.select_one('h3[class~="component-heading"]').text.strip()
    entry.content = item.select_one('h3[class~="component-heading"] + div').text.strip()
    entry.link = item.select_one('a[data-automation-test-id="cta1-"]')['href']

    yield entry

def get_sequential_art(cache, feed_url):
  soup = get_soup('https://collectedcurios.com/sequentialart.php')
  page_title = soup.find('title').text
  cache[feed_url]['name'] = page_title

  entry = Entry()
  entry.title = page_title
  entry.content = soup.select_one('img[class="w3-image"]')
  entry.link = 'https://collectedcurios.com/sequentialart.php'
  last_updated = soup.select_one('div[class~="w3-display-topright"]').text
  m = re.match(r'Last updated: (\d+)(st|nd|rd|th) (\w+) (\d+)', last_updated)
  if not m:
    raise ValueError(f'Could not parse last updated: "{last_updated}"')

  entry.date = int(datetime.strptime(f'{int(m[1]):02} {m[3]} {m[4]}', '%d %B %Y').timestamp())

  yield entry

def get_nerf_now(cache, feed_url):
  soup = get_soup('https://www.nerfnow.com')
  page_title = soup.find('title').text
  cache[feed_url]['name'] = page_title

  entry = Entry()
  entry.title = page_title
  entry.content = soup.select_one('div#comic').text
  entry.link = 'https://www.nerfnow.com'
  last_updated = soup.select_one('meta[property="article:published_time"]')['content']
  entry.date = int(datetime.fromisoformat(last_updated).timestamp())

  yield entry

if __name__ == '__main__':
  for entry in get_sequential_art({'art': {}}, 'art'):
    print(entry)
    print(entry.content)
