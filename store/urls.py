from django.urls import path
from . import views, import_views

urlpatterns = [
    #------------------------- PRODUCTS --------------------
    path('products/', views.products, name='products'),
    path('products/search/', views.products_search, name='products-search'),
    path('product/view/<int:obj_id>', views.product_view, name='product-view'),
    path('product/datas/', views.product_datas, name='product-datas'),
    path('product/prices/', views.product_prices, name='product-prices'),
    path('product/stock/', views.product_stock, name='product-stock'),

    #------------------------- PROVIDERS --------------------
    path('providers/', views.providers, name='providers'),
    path('providers/list/', views.providers_list, name='providers-list'),
    path('providers/search/', views.providers_search, name='providers-search'),
    path('providers/form/', views.providers_form, name='providers-form'),
    path('providers/remove/', views.providers_remove, name='providers-remove'),

    #---------------------- IMPORT -----------------------
    path('import', import_views.import_db, name='import'),
    path('import-db', import_views.import_db_file, name='import-db'),

]
