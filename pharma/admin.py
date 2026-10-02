from django.contrib import admin
from .models import *
from .telegram_models import *
from .external_api_models import ExternalApiCredential, ExternalPatientLookupAudit


class ConfigAdmin(admin.ModelAdmin):
    list_display = ('key', 'value')

class TelegramUserChatAdmin(admin.ModelAdmin):
    list_display = ('code', 'patient', 'telegram_chat_id', 'observations', 'confirmed')

class PacientesAdmin(admin.ModelAdmin):
    list_display = ('n_historial', 'id_user')
    search_fields = ('n_historial', 'id_user__email', 'id_user__first_name', 'id_user__last_name', 'cip')
    list_filter = ('id_user',)
    list_per_page = 500

class PatientSharedAdmin(admin.ModelAdmin):
    list_display = ('patient', 'user')
    list_filter = ('user',)
    list_per_page = 500

class ExternalApiCredentialAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "key_prefix", "active", "created_at", "last_used_at")
    list_filter = ("active",)
    search_fields = ("name", "owner__username", "key_prefix")
    readonly_fields = ("key_prefix", "key_hash", "created_at", "last_used_at")

    def has_add_permission(self, request):
        # Keys are issued by the management command so their secret is shown
        # exactly once and is never stored in the database.
        return False

class ExternalPatientLookupAuditAdmin(admin.ModelAdmin):
    list_display = ("credential", "found", "ip_address", "created_at")
    list_filter = ("found", "created_at")
    readonly_fields = ("credential", "cip_hash", "found", "ip_address", "created_at")
    date_hierarchy = "created_at"


admin.site.register(Config, ConfigAdmin)
admin.site.register(TelegramUserChat, TelegramUserChatAdmin)
admin.site.register(Pacientes, PacientesAdmin)
admin.site.register(PatientShared, PatientSharedAdmin)
admin.site.register(ExternalApiCredential, ExternalApiCredentialAdmin)
admin.site.register(ExternalPatientLookupAudit, ExternalPatientLookupAuditAdmin)
