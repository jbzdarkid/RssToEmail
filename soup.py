import re
from datetime import datetime

import bs4
import requests

from entry import Entry


headers = {
  'User-Agent': 'RssToEmail/0.3 (https://github.com/jbzdarkid/RssToEmail; https://github.com/jbzdarkid/RssToEmail/issues)',
}

def get_entries(cache, feed_url):
  generator = None
  if feed_url == 'bs4|valorant':
    generator = get_valorant_entries
  elif feed_url == 'bs4|microsoft':
    generator = get_microsoft_sus_entries
  elif feed_url == 'bs4|jollyjack':
    generator = get_sequential_art

  found_any = False
  for entry in generator(cache):
    found_any = True
    yield entry

  if not found_any:
    raise ValueError(f'bs4 generator {feed_url} could not find any entries')


# How to create CSS .select filters: https://www.crummy.com/software/BeautifulSoup/bs4/doc/#css-selectors

def get_valorant_entries(cache):
  r = requests.get('https://playvalorant.com/en-us/news/tags/patch-notes', headers=headers)
  r.raise_for_status()
  soup = bs4.BeautifulSoup(r.text, 'html.parser')
  
  for item in soup.select('a[role="button"]'):
    entry = Entry()
    entry.title = item.select_one('div[data-testid="card-title"]').text
    entry.content = item.select_one('div[data-testid="rich-text-html"] > div').text
    entry.link = item['href']
    date_str = item.select_one('div[data-testid="card-date"] > time')['datetime']
    entry.date = int(datetime.fromisoformat(date_str).timestamp())

    yield entry

def get_microsoft_sus_entries(cache):
  r = requests.get('https://www.microsoft.com/en-us/corporate-responsibility/sustainability/report', headers=headers)
  r.raise_for_status()
  soup = bs4.BeautifulSoup(r.text, 'html.parser')

  for item in soup.select('div[class~="material-card"]'):
    entry = Entry()
    entry.title = item.select_one('h3[class~="component-heading"]').text.strip()
    entry.content = item.select_one('h3[class~="component-heading"] + div').text.strip()
    entry.link = item.select_one('a[data-automation-test-id="cta1-"]')['href']

    yield entry

def get_sequential_art(cache):
  r = requests.get('https://collectedcurios.com/sequentialart.php', headers=headers)
  r.raise_for_status()
  soup = bs4.BeautifulSoup(r.text, 'html.parser')

  entry = Entry()
  entry.title = 'Sequential Art'
  entry.content = soup.select_one('img[class="w3-image"]')
  entry.link = 'https://collectedcurios.com/sequentialart.php'
  last_updated = soup.select_one('div[class~="w3-display-topright"]').text
  m = re.match('Last updated: (\d+)(st|nd|rd|th) (\w+) (\d+)', last_updated)
  if not m:
    raise ValueError(f'Could not parse last updated: "{last_updated}"')

  entry.date = int(datetime.strptime(f'{m[1]:02} {m[3]} {m[4]}', '%d %B %Y').timestamp())

  yield entry


if __name__ == '__main__':
  for entry in get_sequential_art(None):
    print(entry)
