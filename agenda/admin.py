from django.contrib import admin
from .models import *

class NoteAdmin(admin.ModelAdmin):
    list_display = ('name', 'ini_date', 'end_date', 'common')
    list_filter = ['common'] 

class StatusAdmin(admin.ModelAdmin):
    list_display = ('code', 'name')

admin.site.register(Note, NoteAdmin)
admin.site.register(Status, StatusAdmin)
