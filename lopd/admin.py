from django.contrib import admin
from .models import *


class LOPDTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'company')

admin.site.register(LOPDConsents)
admin.site.register(LOPDTemplate, LOPDTemplateAdmin)
