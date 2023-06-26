from django.contrib import admin
from params.models import BloodPressure

class BloodPressureAdmin(admin.ModelAdmin):
    list_display = ('creation_date',)


admin.site.register(BloodPressure, BloodPressureAdmin)
