from django.urls import path
from bibliomecum import views

urlpatterns = [
    #------------------------- ORGANIZATIONS --------------------
    path('bibliomecum/form/', views.receipts_form, name='bibliomecum-receipts-form'),
    path('bibliomecum/isbn-add/', views.receipts_isbn_add, name='bibliomecum-receipts-isbn-add'),
    path('bibliomecum/isbn-remove/', views.receipts_isbn_remove, name='bibliomecum-receipts-isbn-remove'),
    path('bibliomecum/atc-add/', views.receipts_atc_add, name='bibliomecum-receipts-atc-add'),
    path('bibliomecum/atc-remove/', views.receipts_atc_remove, name='bibliomecum-receipts-atc-remove'),
    path('bibliomecum/ciap-add/', views.receipts_ciap_add, name='bibliomecum-receipts-ciap-add'),
    path('bibliomecum/ciap-remove/', views.receipts_ciap_remove, name='bibliomecum-receipts-ciap-remove'),
    path('bibliomecum/remove/', views.receipts_remove, name='bibliomecum-receipts-remove'),
    path('bibliomecum/print/<int:obj_id>/', views.receipts_print, name='bibliomecum-receipts-print'),
    path('bibliomecum/isbn-search/', views.isbn_search, name='bibliomecum-isbn-search'),
]
