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
                #Admin
                if request.user.is_superuser:
                    return f(request, *args, **kwargs)
                #Managers y Empleados
                if not check_user_payment(request.user):
                    #logout(request)
                    return redirect('account-payment-error')
                if bool(request.user.groups.filter(name__in=group_names)) or request.user.is_superuser:
                    return f(request, *args, **kwargs)
                else:
                	return (render(request, "error_exception.html", {'exc':"This user have not permission to access to this section"}))
            return redirect('auth_login')
        return _arguments_wrapper
    return _method_wrapper

def group_required_pwa(*group_names):
    def _method_wrapper(f):
        def _arguments_wrapper(request, *args, **kwargs) :
            if request.user.is_authenticated:
                if bool(request.user.groups.filter(name__in=group_names)) or request.user.is_superuser:
                    return f(request, *args, **kwargs)
                else:
                	return (render(request, "error_exception.html", {'exc':"This user have not permission to access to this section"}))
            return redirect('pwa-login')
        return _arguments_wrapper
    return _method_wrapper

