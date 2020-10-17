from threading import Thread
from flask import current_app, render_template
from flask_mail import Message
from . import mail

def send_asnc_mail(app, msg):
    with app.app_context(): # Artificially creating context of app at that particular time since send() need it
        mail.send(msg) # This takes a long time to executee so it is run in a separate thread

def send_email(to, subject, template, **kwargs):
    app = current_app._get_current_object()

    subject = app.config.get('TEST_MAIL_SUBJECT_PREFIX') + subject
    msg = Message(subject, sender=app.config.get('TEST_MAIL_SENDER'), recipients=[to])
    msg.body = render_template(template + '.txt', **kwargs)
    msg.html = render_template(template + '.html', **kwargs)

    thr = Thread(target=send_asnc_mail, args=[app, msg])
    thr.start()
    return thr
