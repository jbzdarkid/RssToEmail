from smtplib import SMTP
from email.message import EmailMessage
from email.mime.text import MIMEText

FROM = ''
TO = ''

msg = EmailMessage()
msg['Subject'] = 'Witness puzzle'
msg['To'] = '%s <%s>' % (TO.split('@')[0], TO)
msg['From'] = FROM
msg['Date'] = DATE

msg.attach(MIMEText("""
the body goes here
""", 'html'))

server = SMTP('smtp.gmail.com', 587)
server.ehlo()
server.starttls()
server.login(FROM, environ['PASSWORD'])
server.sendmail(FROM, TO, msg.as_string())
server.quit()
