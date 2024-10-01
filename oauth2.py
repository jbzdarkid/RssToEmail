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

  def __enter__(self):
    self.connection = smtplib.SMTP_SSL('smtp.gmail.com', context=ssl.create_default_context())
    self.connection.ehlo()
    auth_string = self.get_auth_string()
    self.connection.docmd('AUTH', 'XOAUTH2 ' + base64.b64encode(auth_string.encode('utf-8')).decode('utf-8'))
    return self

  def sendmail(self, from_addr, to_addrs, msg):
    return self.connection.sendmail(from_addr, to_addrs, msg)
    
  def __exit__(self, exc_type, exc_value, traceback):
    self.connection.quit()

  def get_auth_string(self):
    params = {
      'grant_type': 'refresh_token',
      'client_id': self.client_id,
      'client_secret': self.client_secret,
      'refresh_token': self.refresh_token,
    }

    r = requests.post('https://accounts.google.com/o/oauth2/token', params=params)
    r.raise_for_status()
    access_token = r.json()['access_token']

    return 'user=%s\1auth=Bearer %s\1\1' % (self.username, access_token)
