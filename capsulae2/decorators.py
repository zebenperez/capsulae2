from django.shortcuts import render, redirect
#from django.contrib.auth import logout
from capsulae2.capsulae_lib import check_user_payment

import logging
logger = logging.getLogger(__name__)

def group_required(*group_names):
    def _method_wrapper(f):
        def _arguments_wrapper(request, *args, **kwargs) :
            logger.info("[{}]: \"{}\"".format(request.user, request.path_info))
            if request.user.is_authenticated:
                if not check_user_payment(request.user):
                    #logout(request)
                    return redirect('account-payment-error')
                if bool(request.user.groups.filter(name__in=group_names)) or request.user.is_superuser:
                    return f(request, *args, **kwargs)
            return redirect('auth_login')
        return _arguments_wrapper
    return _method_wrapper

