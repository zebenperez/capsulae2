from django.contrib import admin
from .models import *

class JourneyAdmin(admin.ModelAdmin):
    list_display = ('user', 'ini_date', 'end_date', 'started')

admin.site.register(Journey, JourneyAdmin)
