from django.contrib import admin
from .models import *


class MenuAdmin(admin.ModelAdmin):
    list_display = ("code", "name",)

class ProfileAdmin(admin.ModelAdmin):
    list_display = ("name", "amount", "discount", "active")
    filter_horizontal = ('menus',)

class UserMenuAdmin(admin.ModelAdmin):
    list_display = ("user",)
    filter_horizontal = ('menus',)

admin.site.register(Company)
admin.site.register(Menu, MenuAdmin)
admin.site.register(Profile, ProfileAdmin)
admin.site.register(UserMenu, UserMenuAdmin)
