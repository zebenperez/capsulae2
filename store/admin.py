from django.contrib import admin
from .models import *


class PriceAdmin(admin.ModelAdmin):
    list_display = ('product', 'amount', 'date', 'sale')

class ProductTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'company')
    list_filter = ('company',)

class ProductAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'company', 'remote_store', 'online', 'deprecated')
    list_filter = ('remote_store', 'online', 'deprecated', 'company')
    search_fields = ('code', 'name', 'extra1')

class ProviderAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'company')
    list_filter = ('company',)

class StoreInflowAdmin(admin.ModelAdmin):
    list_display = ('quantity', 'product')

class StoreOutflowAdmin(admin.ModelAdmin):
    list_display = ('quantity', 'product')

class PurchaseDeliveryNoteAdmin(admin.ModelAdmin):
    list_display = ('document_type', 'document_number', 'document_date', 'provider', 'company', 'lines_count', 'total_amount')
    list_filter = ('company', 'status', 'document_type')
    search_fields = ('document_number', 'provider__name')

class TaxAdmin(admin.ModelAdmin):
    list_display = ('name', 'percent', 'company')
    list_filter = ('company',)

admin.site.register(Price, PriceAdmin)
admin.site.register(Product, ProductAdmin)
admin.site.register(ProductType, ProductTypeAdmin)
admin.site.register(Provider, ProviderAdmin)
admin.site.register(StoreInflow, StoreInflowAdmin)
admin.site.register(StoreOutflow, StoreOutflowAdmin)
admin.site.register(PurchaseDeliveryNote, PurchaseDeliveryNoteAdmin)
admin.site.register(Tax, TaxAdmin)
