from django.contrib import admin
from .models import *


class CompanyAdmin(admin.ModelAdmin):
    list_display = ("name", "code")
    filter_horizontal = ('users',)

class ConfigAdmin(admin.ModelAdmin):
    list_display = ("key", "value",)

class DonationAdmin(admin.ModelAdmin):
    list_display = ("pay_date", "name", "cif", "email", "plan", "amount", "confirm")

class EmployeeProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "pin")

class MenuAdmin(admin.ModelAdmin):
    list_display = ("code", "name",)

class PlanAdmin(admin.ModelAdmin):
    list_display = ("name", "days", "amount", "active", "payment_link")

class ProfileAdmin(admin.ModelAdmin):
    list_display = ("name", "amount", "active")
    filter_horizontal = ('menus',)

class UserMenuAdmin(admin.ModelAdmin):
    list_display = ("user",)
    filter_horizontal = ('menus',)

class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "profile")

class UserPaymentAdmin(admin.ModelAdmin):
    #list_display = ("user", "amount", "pay_date", "expire_date", "confirm", "donation")
    list_display = ("user", "amount", "pay_date", "expire_date", "confirm")

admin.site.register(Config, ConfigAdmin)
admin.site.register(Company, CompanyAdmin)
admin.site.register(Donation, DonationAdmin)
admin.site.register(Menu, MenuAdmin)
admin.site.register(Plan, PlanAdmin)
admin.site.register(Profile, ProfileAdmin)
admin.site.register(UserMenu, UserMenuAdmin)
admin.site.register(UserProfile, UserProfileAdmin)
admin.site.register(UserPayment, UserPaymentAdmin)
#admin.site.register(EmployeeProfile, ExployeeProfileAdmin)
admin.site.register(EmployeeProfile, EmployeeProfileAdmin)
