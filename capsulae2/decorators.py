from django.shortcuts import render, redirect

import logging
logger = logging.getLogger(__name__)

def group_required(*group_names):
    def _method_wrapper(f):
        def _arguments_wrapper(request, *args, **kwargs) :
            logger.info("[{}]: \"{}\"".format(request.user, request.path_info))
            if request.user.is_authenticated:
                if bool(request.user.groups.filter(name__in=group_names)) or request.user.is_superuser:
                    return f(request, *args, **kwargs)
            return redirect('auth_login')
        return _arguments_wrapper
    return _method_wrapper

