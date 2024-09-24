from account.models import UserPayment
from datetime import datetime

def check_user_payment(user):
    now = datetime.now()
    up = UserPayment.objects.filter(user = user, expire_date__gte = now).first()
    if up == None:
        return False
    return True


