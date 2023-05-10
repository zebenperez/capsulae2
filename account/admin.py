from django.contrib import admin
from .models import *


class MenuAdmin(admin.ModelAdmin):
    list_display = ("code", "name",)

class UserMenuAdmin(admin.ModelAdmin):
    list_display = ("user",)
    filter_horizontal = ('menus',)

admin.site.register(Company)
admin.site.register(Menu, MenuAdmin)
admin.site.register(UserMenu, UserMenuAdmin)
