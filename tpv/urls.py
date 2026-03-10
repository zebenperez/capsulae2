from django.urls import include, path, re_path
from . import views, api

urlpatterns = [
    path('', views.index, name='tpv-index'),
    path('product-by-code/', views.product_by_code, name='tpv-product-by-code'),
    path('client-by-code/', views.client_by_code, name='tpv-client-by-code'),

    path('add-tpv-line/', views.tpv_add_product, name='tpv-add-product'),
    #path('add-tpv-line/<int:product_id>/<slug:hashinv>/', views.tpv_add_product, name='tpv-add-product'),
    path('remove-tpv-line/', views.remove_tpv_line, name='tpv-remove-line'),
    #path('remove-tpv-line/<int:id_line>/', views.remove_tpv_line, name='tpv-remove-line'),
    path('change-units-tpv-line/', views.change_units_tpv_line, name='change-units-tpv-line'),
    path('chante-method/', views.change_method, name='change-method'),
    path('chante-regulated/', views.change_regulated, name='change-regulated'),
    path('print-sale/<slug:hashinv>/', views.print_sale, name='print-sale'),
    path('print-invoice-sale/<slug:hashinv>/', views.print_invoice_sale, name='print-invoice-sale'),
    path('print-invoice-client/', views.print_invoice_client, name='print-invoice-client'),
    path('print-invoice-client-save/', views.print_invoice_client_save, name='print-invoice-client-save'),
    path('confirm-sale/<slug:hashinv>/', views.confirm_sale, name='confirm-sale'),
    path('cancel-sale/<slug:hashinv>/', views.cancel_sale, name='cancel-sale'),
    path('remove-sale/<slug:hashinv>/', views.remove_sale, name='remove-sale'),

    path('sales/<int:days>/', views.sales, name='get-sales'),
    path('sales/', views.sales, name='get-sales'),
    path('save-paid-amount/', views.save_paid_amount, name='save-paid-amount'),

    path('api/from-cms/', api.from_cms, name='from-cms'),
    path('api/finish-from-cms/', api.finish_from_cms, name='finish-from-cms'),

    path('order/<slug:hashinv>/', views.order_detail, name='view-order'),
    path('order/confirm/<slug:hashinv>/<int:cash>/', views.order_confirm, name='confirm-order'),
    path('order/confirm/<slug:hashinv>/', views.order_confirm, name='confirm-order'),
    path('order/ready/<slug:hashinv>/', views.order_ready, name='ready-order'),
    path('orders/<int:days>/', views.orders, name='get-orders'),
    path('orders/', views.orders, name='get-orders'),
    path('orders/get-n-pending/', views.get_orders_number, name='get-n-orders'),
    
    #path('zeta/<int:days>/', views.zeta, name='zeta'),
    path('zeta/<slug:month>/', views.zeta, name='zeta'),
    path('zeta/', views.zeta, name='zeta'),

]

