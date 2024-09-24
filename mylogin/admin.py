from django.contrib import admin
from django.http.request import HttpRequest
from django.template.response import TemplateResponse
from .models import *

# Register your models here.
class ExternalAuthAdmin(admin.ModelAdmin):
    list_display = ('localusername','username','domain', 'update')
    search_fields = ['username', 'localusername', 'domain']

    def changelist_view(self, request,  extra_context=None):
        q = request.GET.copy()
        q['domain'] = request.get_host()
        request.GET = q
        request.META['QUERY_STRING'] = request.GET.urlencode()

        return super().changelist_view(request, extra_context=extra_context)

admin.site.register(ExternalAuth, ExternalAuthAdmin)
