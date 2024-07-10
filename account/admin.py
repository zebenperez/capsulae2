from django.contrib import admin
from .models import *


class CompanyAdmin(admin.ModelAdmin):
    list_display = ("name", "code")
    filter_horizontal = ('users',)

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

class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "profile")

class UserPaymentAdmin(admin.ModelAdmin):
    list_display = ("user", "amount", "pay_date", "expire_date")

admin.site.register(Config, ConfigAdmin)
admin.site.register(Company, CompanyAdmin)
admin.site.register(Menu, MenuAdmin)
admin.site.register(Plan, PlanAdmin)
admin.site.register(Profile, ProfileAdmin)
admin.site.register(UserMenu, UserMenuAdmin)
admin.site.register(UserProfile, UserProfileAdmin)
admin.site.register(UserPayment, UserPaymentAdmin)
