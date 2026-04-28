from django.shortcuts import render
from capsulae2.decorators import group_required
from .models import *


@group_required("admins",)
def signup(request):
    email = request.POST.get('email','')
    confirmedemail = request.POST.get('confirmedemail','')

    user = None
    useractivate = None
    if (email == confirmedemail):
        if validate_captcha(request):
            try:
                password = ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(8))
                if not User.objects.filter(username=email).exists():
                    user = User.objects.create_user(email, email, password)
                    user.first_name = request.POST.get('name')
                    user.last_name = request.POST.get('cif')
                    user.save()
                    profile = EmployeeProfile(user=user)
                    profile.save()
                    useractivate = UserActivate()
                    useractivate.user = user
                    useractivate.activate_key = ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(128))
                    useractivate.save()
                    html_message = 'Gracias por tu inter&eacute;s en Capsulae. Para la activaci&oacute;n de la cuenta pincha <a href="http://%s/pharma/activate_account/%s/">aqu&iacute;</a>' % (request.META['HTTP_HOST'], useractivate.activate_key)
                    send_mail('Registro en Capsulae', 'Registro en Capsulae', 'info@shidix.com', [email], html_message=html_message)
                    context = {'user':user, 'useractivate':useractivate, 'error_code':0}
                    LogManager(user=user, app=CAT_REGISTER).save_action(request.path, "Usuario registrado sin confirmar")
                else:
                    user = User.objects.get(email=email)
                    context = {'user':user, 'useractivate':useractivate, 'error_code':1}
            except Exception as e:
                print(e)
                context = {'user':user, 'useractivate':useractivate, 'error_code':2, 'error_msg':e}
        else:
            context = {'error_msg': 'Error de validación del captcha' }
    return render (request, "account/signup.html", context)

