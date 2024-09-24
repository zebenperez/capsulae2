from django.contrib import admin
from .models import *
from .telegram_models import *


class ConfigAdmin(admin.ModelAdmin):
    list_display = ('key', 'value')

class TelegramUserChatAdmin(admin.ModelAdmin):
    list_display = ('code', 'patient', 'telegram_chat_id', 'confirmed')

class PacientesAdmin(admin.ModelAdmin):
    list_display = ('n_historial', 'id_user')
    search_fields = ('n_historial', 'id_user__email', 'id_user__first_name', 'id_user__last_name')

admin.site.register(Config, ConfigAdmin)
admin.site.register(TelegramUserChat, TelegramUserChatAdmin)
admin.site.register(Pacientes, PacientesAdmin)
