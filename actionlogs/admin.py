from django.contrib import admin
from .models import *


class ActionLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'date', 'url', 'action')
    #search_fields = ('n_historial', 'id_user__email', 'id_user__first_name', 'id_user__last_name', 'cip')
    list_filter = ('user',)

admin.site.register(ActionLog, ActionLogAdmin)
