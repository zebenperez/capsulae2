from django.core.mail import send_mail


def send_email(subject, body, email_from, email_to, html_body=""):
    send_mail(subject, body, email_from, email_to, html_message=html_body)

def send_register_email(host, activate_key, email_to):
    html_message = 'Gracias por tu inter&eacute;s en Capsulae. Para la activaci&oacute;n de la cuenta pincha'
    html_message = '{} <a href="http://{}/account/activate_account/{}/">aqu&iacute;</a>'.format(html_message, host, activate_key)
    send_email('Registro en Capsulae', 'Registro en Capsulae', 'info@shidix.com', email_to, html_message)

def send_new_password_email(password, email_to):
    send_mail('Tu nuevo password en Capsulae', 'Tu nuevo password en Capsulae es %s' % password, 'info@shidix.com', email_to)

