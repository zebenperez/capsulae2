from django.urls import path
from . import views, import_views

urlpatterns = [
    path('select-company/', views.store_company_select, name='store-company-select'),
    #------------------------- PRODUCTS --------------------
    path('products/', views.products, name='products'),
    path('products/search/', views.products_search, name='products-search'),
    path('products/new/', views.product_new, name='product-new'),
    path('products/import-albaran/', views.product_albaran_import, name='product-albaran-import'),
    path('delivery-notes/', views.purchase_delivery_notes, name='purchase-delivery-notes'),
    path('delivery-notes/<int:obj_id>/', views.purchase_delivery_note_detail, name='purchase-delivery-note-detail'),
    path('delivery-notes/<int:obj_id>/lines/', views.purchase_delivery_note_lines, name='purchase-delivery-note-lines'),
    path('delivery-notes/<int:obj_id>/remove/', views.purchase_delivery_note_remove, name='purchase-delivery-note-remove'),
    path('products/remove/<int:obj_id>/', views.product_remove, name='product-remove'),
    path('product/view/<int:obj_id>', views.product_view, name='product-view'),
    path('product/datas/', views.product_datas, name='product-datas'),
    path('product/prices/', views.product_prices, name='product-prices'),
    path('product/price/new/', views.product_price_new, name='product-price-new'),
    path('product/view/<int:obj_id>/price-summary/', views.product_price_summary, name='product-price-summary'),
    path('product/view/<int:obj_id>/stock-summary/', views.product_stock_summary, name='product-stock-summary'),
    path('product/stock/', views.product_stock, name='product-stock'),

    #------------------------- PROVIDERS --------------------
    path('providers/', views.providers, name='providers'),
    path('providers/list/', views.providers_list, name='providers-list'),
    path('providers/search/', views.providers_search, name='providers-search'),
    path('providers/form/', views.providers_form, name='providers-form'),
    path('providers/remove/', views.providers_remove, name='providers-remove'),

    #------------------------- CLIENTS ----------------------
    path('clients/', views.clients, name='clients'),
    path('clients/list/', views.clients_list, name='clients-list'),
    path('clients/search/', views.clients_search, name='clients-search'),
    path('clients/form/', views.clients_form, name='clients-form'),
    path('clients/remove/', views.clients_remove, name='clients-remove'),

    #---------------------- IMPORT -----------------------
    path('import', import_views.import_db, name='import'),
    path('import-db', import_views.import_db_file, name='import-db'),

]
