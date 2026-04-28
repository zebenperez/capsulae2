from django.urls import path
from . import views

urlpatterns = [
    #------------------------- PATIENTS --------------------
    path('medication/', views.medication, name='medication'),
    #path('medication/list/', views.medication_list, name='medication-list'),
    path('medication/search/', views.medication_search, name='medication-search'),

    path('medication/print-tag/<int:medication_id>/', views.medication_print_tag, name='medication-print-tag'),

    path('medication/update-cache/', views.update_cache, name='medication-update-cache'),
    path('medication/update-cache-box/', views.update_cache_box, name='medication-update-cache-box'),
]
