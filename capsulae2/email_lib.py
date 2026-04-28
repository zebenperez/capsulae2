from django.core.mail import send_mail
from django.conf import settings


def send_email(subject, body, email_to, html_body=""):
    try:
        email_from = settings.EMAIL_FROM_DEFAULT
    except:
        email_from = "noresponse@fundec.org"
    send_mail(subject, body, email_from, email_to, html_message=html_body)

def send_register_email(host, activate_key, email_to):
    html_message = 'Gracias por tu inter&eacute;s en Capsulae. Para la activaci&oacute;n de la cuenta pincha'
    html_message = '{} <a href="http://{}/account/activate_account/{}/">aqu&iacute;</a>'.format(html_message, host, activate_key)
    #send_email('Registro en Capsulae', 'Registro en Capsulae', 'info@shidix.com', email_to, html_message)
    send_email('Registro en Capsulae', 'Registro en Capsulae', email_to, html_message)

def send_new_password_email(password, email_to):
    #send_mail('Tu nuevo password en Capsulae', 'Tu nuevo password en Capsulae es %s' % password, 'info@shidix.com', email_to)
    send_email('Tu nuevo password en Capsulae', 'Tu nuevo password en Capsulae es %s' % password, email_to)

def send_derivation_email(emails, html):
    send_email('Derivación de paciente', 'Derivación de paciente', emails, html_body=html)

def send_import_doc_email(host, email_to, name, file_name):
    html_message = f'Hola {name}.<br/>'
    html_message += f'La fundación FÜNDEC ha subido un nuevo documento ({file_name}) a su carpeta personal de la app capsulae.<br/>'
    html_message += f'Puede consultarlo accediendo al siguiente enlace introduciendo su PIN (NIF/NIE/Pasaporte):'
    html_message += f'<a href="https://{host}/pwa/">aqu&iacute;</a>'
    html_message += f'<br/><br/>Un afectuoso saludo<br/>'
    html_message += f'El equipo de Fundec'
    subject = 'Notificación Fundec. Ha recibido un nuevo documento'
    send_email(subject, '', email_to, html_message)


