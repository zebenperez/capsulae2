from django.urls import path
from bibliomecum import views

urlpatterns = [
    #------------------------- ORGANIZATIONS --------------------
    path('bibliomecum/form/', views.receipts_form, name='bibliomecum-receipts-form'),
    path('bibliomecum/isbn-add/', views.receipts_isbn_add, name='bibliomecum-receipts-isbn-add'),
    path('bibliomecum/isbn-remove/', views.receipts_isbn_remove, name='bibliomecum-receipts-isbn-remove'),
    path('bibliomecum/remove/', views.receipts_remove, name='bibliomecum-receipts-remove'),
    path('bibliomecum/print/<int:obj_id>/', views.receipts_print, name='bibliomecum-receipts-print'),
]
