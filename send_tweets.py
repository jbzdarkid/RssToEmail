import sys
from email.message import EmailMessage
from os import environ
from time import localtime, sleep, strftime

import twitter
from oauth2 import EmailServer

TARGET_EMAIL = environ.get('target_email', None)
SENDER_EMAIL = environ.get('sender_email', None)

if __name__ == '__main__':
  if len(sys.argv) < 1:
    print('Please provide the twitter handle as the first argument')
    exit(1)
  handle = sys.argv[1]
  user_id = twitter.get_user_id(handle)
  tweets = twitter.get_entries(user_id)
  tweets.sort(key = lambda e: e.date if e.date else 0)

  msg = EmailMessage()
  msg['Subject'] = f'{len(tweets)} tweets from {handle} ({user_id})'
  msg['From'] = f'"Twitter user {handle}" <{SENDER_EMAIL}>'
  msg['To'] = TARGET_EMAIL
  msg['Reply-To'] = TARGET_EMAIL
  email_body = ''
  for t in tweets:
    email_body += '<hr><br>'
    email_body += f'<a href="{t.link}">Tweet</a> sent at ' + strftime("%A, %B %d, %Y", localtime(t.date)) + '\n'
    email_body += t.content + '\n'

  msg.set_content("Hello, world")
  msg.add_alternative(email_body.replace('\n', '<br>'), subtype='html')

  with EmailServer() as email_server:
    email_server.sendmail(SENDER_EMAIL, TARGET_EMAIL, msg.as_string())
