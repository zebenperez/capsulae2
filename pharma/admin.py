from django.contrib import admin
from .models import *


class ConfigAdmin(admin.ModelAdmin):
    list_display = ('key', 'value')

admin.site.register(Config, ConfigAdmin)
