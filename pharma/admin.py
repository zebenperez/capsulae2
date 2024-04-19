from django.contrib import admin
from .models import *
from .telegram_models import *


class ConfigAdmin(admin.ModelAdmin):
    list_display = ('key', 'value')

class TelegramUserChatAdmin(admin.ModelAdmin):
    list_display = ('code', 'patient', 'telegram_chat_id', 'confirmed')

admin.site.register(Config, ConfigAdmin)
admin.site.register(TelegramUserChat, TelegramUserChatAdmin)
