from account.models import UserPayment
from datetime import datetime

def check_user_payment(user):
#    try:
#        emp = user.employee_profile
#        comp = emp.company.manager
#    except:
#        comp = user
#    up = UserPayment.objects.filter(user=comp, cancel=False, confirm=True, expire_date__gte=now).first()
    now = datetime.now()
    up = UserPayment.objects.filter(user=user, cancel=False, confirm=True, expire_date__gte=now).first()
    if up == None:
        return False
    return True


