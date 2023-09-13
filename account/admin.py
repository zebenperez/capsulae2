from django.contrib import admin
from .models import *


class ConfigAdmin(admin.ModelAdmin):
    list_display = ("key", "value",)

class MenuAdmin(admin.ModelAdmin):
    list_display = ("code", "name",)

class PlanAdmin(admin.ModelAdmin):
    list_display = ("name", "days", "amount", "active")

class ProfileAdmin(admin.ModelAdmin):
    list_display = ("name", "amount", "active")
    filter_horizontal = ('menus',)

class UserMenuAdmin(admin.ModelAdmin):
    list_display = ("user",)
    filter_horizontal = ('menus',)

admin.site.register(Config, ConfigAdmin)
admin.site.register(Company)
admin.site.register(Menu, MenuAdmin)
admin.site.register(Plan, PlanAdmin)
admin.site.register(Profile, ProfileAdmin)
admin.site.register(UserMenu, UserMenuAdmin)
