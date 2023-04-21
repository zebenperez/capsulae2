from django.contrib import admin
from .models import *

# Register your models here.
class ExternalAuthAdmin(admin.ModelAdmin):
    list_display = ('localusername','username','domain', 'update')
    search_fields = ['username', 'localusername', 'domain']

admin.site.register(ExternalAuth, ExternalAuthAdmin)
