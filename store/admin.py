from django.contrib import admin
from .models import *


class PriceAdmin(admin.ModelAdmin):
    list_display = ('product', 'amount', 'date', 'sale')

class ProductTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'company')
    list_filter = ('company',)

class ProviderAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'company')
    list_filter = ('company',)

class StoreInflowAdmin(admin.ModelAdmin):
    list_display = ('quantity', 'product')

class StoreOutflowAdmin(admin.ModelAdmin):
    list_display = ('quantity', 'product')

class TaxAdmin(admin.ModelAdmin):
    list_display = ('name', 'percent', 'company')
    list_filter = ('company',)

admin.site.register(Price, PriceAdmin)
admin.site.register(Product)
admin.site.register(ProductType, ProductTypeAdmin)
admin.site.register(Provider, ProviderAdmin)
admin.site.register(StoreInflow, StoreInflowAdmin)
admin.site.register(StoreOutflow, StoreOutflowAdmin)
admin.site.register(Tax, TaxAdmin)

