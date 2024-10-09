import base64
import os
import requests
import smtplib
import ssl

# Adapted from Google's https://github.com/google/gmail-oauth2-tools/blob/master/python/oauth2.py
class EmailServer():
  def __init__(self):
    self.username = os.environ.get('sender_email', None)
    self.client_id = os.environ.get('email_client_id', None)
    self.client_secret = os.environ.get('email_client_secret', None)
    self.refresh_token = os.environ.get('email_refresh_token', None)
    self.connection = None

  def __enter__(self):
    if not self.refresh_token:
      return self # Local testing, etc

    self.connection = smtplib.SMTP_SSL('smtp.gmail.com', context=ssl.create_default_context())
    self.connection.ehlo()
    auth_string = self.get_auth_string()
    self.connection.docmd('AUTH', 'XOAUTH2 ' + base64.b64encode(auth_string.encode('utf-8')).decode('utf-8'))
    return self

  def sendmail(self, from_addr, to_addrs, msg):
    return self.connection.sendmail(from_addr, to_addrs, msg)
    
  def __exit__(self, exc_type, exc_value, traceback):
    if self.connection:
      self.connection.quit()

  def get_refresh_token(self, client_secret, auth_code):
    params = {
      'grant_type': 'authorization_code',
      'redirect_uri': 'https://oauth2.dance/',
      'client_id': self.client_id,
      'client_secret': client_secret,
      'code': auth_code,
    }

    r = requests.post('https://accounts.google.com/o/oauth2/token', params=params)
    if not r.ok:
      print(r.status_code, r.text)
    return r.json()['refresh_token']

  def get_auth_string(self):
    params = {
      'grant_type': 'refresh_token',
      'client_id': self.client_id,
      'client_secret': self.client_secret,
      'refresh_token': self.refresh_token,
    }

    r = requests.post('https://accounts.google.com/o/oauth2/token', params=params)
    if not r.ok:
      print(r.status_code, r.text)
    access_token = r.json()['access_token']

    return 'user=%s\1auth=Bearer %s\1\1' % (self.username, access_token)

if __name__ == '__main__':
  with EmailServer() as server:
    server.client_id = input('Client id: ')

    print('Please visit this URL:')
    print('https://accounts.google.com/o/oauth2/auth', end='')

    print('?access_type=offline', end='')
    print('&prompt=consent', end='')
    print('&response_type=code', end='')
    print('&redirect_uri=https%3A%2F%2Foauth2.dance%2F', end='')
    print('&scope=https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fgmail.send', end='')
    print(f'&client_id={server.client_id}')

    auth_code = input('Enter auth code: ')
    client_secret = input('Client secret: ')
    print('Refresh token:', server.get_refresh_token(client_secret, auth_code))
