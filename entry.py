from email.message import EmailMessage
from os import environ
from time import localtime, sleep, strftime

TARGET_EMAIL = environ.get('target_email', None)
SENDER_EMAIL = environ.get('sender_email', None)

# TODO: https://web.dev/color-scheme/ -- try sending dark mode emails?

class Entry:
    def __init__(self):
        self.content = '(This RSS entry has no contents)'
        self.date = None

    def __repr__(self):
        return f'Entry(title={self.title}, date={self.date}, link={self.link}, content={len(self.content)})'

    def send_email(self, email_server, feed_title):
        msg = EmailMessage()
        msg['Subject'] = self.title.replace('\n', '').replace('\r', '')
        msg['To'] = TARGET_EMAIL
        if feed_title is None:
            feed_title = '(Unknown feed title)'
        escaped_from = feed_title.replace('"', '\\"').replace(':', '')
        msg['From'] = f'"{escaped_from}" <{SENDER_EMAIL}>'
        msg['Reply-To'] = TARGET_EMAIL

        # Contents truncated at 50k characters to avoid going over google's "message clipped" limit. I always want the "full post" link to be visible.
        plaintext = f'{self.content[:50_000]}\n\nTo view the full post, click here: {self.link}'
        if self.date:
            plaintext += f'\nThis was originally posted at {strftime("%A, %B %d, %Y", localtime(self.date))}.'
        richtext = plaintext.replace('\n', '<br>')

        msg.set_content(plaintext)
        msg.add_alternative(richtext, subtype='html')
        if SENDER_EMAIL and TARGET_EMAIL:
            email_server.sendmail(SENDER_EMAIL, TARGET_EMAIL, msg.as_string())
            sleep(5) # Avoid hitting throttling limits
        else:
            print(f'{feed_title}: {self.title}')
            print(self.content)
            print()
