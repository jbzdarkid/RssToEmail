# A very light smattering of tests
import inspect
import sys
from pathlib import Path
from unittest.mock import patch

from entry import Entry
import rss_to_email as main

_id = 0
def get_id():
  global _id
  _id += 1
  return _id

class MockEntry:
  def __init__(self, date):
    self.id = get_id()
    self.title = f'Title {self.id}'
    self.link = f'https://example.com/{self.id}'
    self.date = date
    self.content = f'Entry {self.id} contents'
    self.sent = False

  def __repr__(self):
    return f'MockEntry(id={self.id}, sent={self.sent})'

  def send_email(self, *args):
    self.sent = True

class Tests:
  feed_url = 'https://example.com'
  feed_name = 'Test feed'

  def mock_get_entries(self, *dates):
    return main.wrap_generator(self.feed_name, self.feed_url, lambda: (MockEntry(date) for date in dates))

  #############
  #!# Tests #!#
  #############
  def test_new_feed(self):
    main.cache = {}
    entries = self.mock_get_entries(1, 2, 3)
    main.handle_entries(entries, None)
    assert not entries[0].sent
    assert not entries[1].sent
    assert not entries[2].sent

    assert main.cache[self.feed_url]['last_updated'] == 100
    assert len(main.cache[self.feed_url]['seen_entries']) == 0

  def test_existing_feed(self):
    main.cache[self.feed_url]['last_updated'] = 0
    entries = self.mock_get_entries(1, 2, 3)
    main.handle_entries(entries, None)
    assert entries[0].sent
    assert entries[1].sent
    assert entries[2].sent

  def test_existing_feed_by_url(self):
    del main.cache[self.feed_url]['last_updated']
    entries = self.mock_get_entries(None, None, None)
    main.handle_entries(entries, None)
    assert entries[0].sent
    assert entries[1].sent
    assert entries[2].sent

  def test_simulatneous_entries(self):
    entries = self.mock_get_entries(200, 200, 200)
    main.handle_entries(entries, None)
    assert entries[0].sent
    assert entries[1].sent
    assert entries[2].sent

    entries[0].sent = False
    entries[1].sent = False
    entries[2].sent = False
    main.handle_entries(entries, None)
    assert not entries[0].sent
    assert not entries[1].sent
    assert not entries[2].sent


if __name__ == '__main__':
  test_class = Tests()
  with patch('rss_to_email.time') as mock_time:
    mock_time.return_value = 100

    main.cache = {}
    main.cache_name = 'test_entries.json'
    Path(main.cache_name).unlink(missing_ok=True)

    def is_test(method):
      return inspect.ismethod(method) and method.__name__.startswith('test')
    tests = list(inspect.getmembers(test_class, is_test))
    tests.sort(key=lambda func: func[1].__code__.co_firstlineno)

    for test in tests:
      if len(sys.argv) > 1: # Requested specific test(s)
        if test[0] not in sys.argv[1:]:
          continue

      # Test setup
      main.cache[test_class.feed_url] = {'last_updated': 0, 'name': test_class.feed_name, 'seen_entries': []}

      # Run test
      print('---', test[0], 'started')
      try:
        test[1]()
      except Exception:
        print('!!!', test[0], 'failed:')
        import traceback
        traceback.print_exc()
        sys.exit(-1)

    print('===', test[0], 'passed')
  print('\nAll tests passed')
