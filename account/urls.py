from django.urls import path
from . import views

urlpatterns = [
    path('signup/', views.signup, name='account-signup'),
    path('privacy-policy/', views.privacy_policy, name='privacy-policy'),

    #------------------------- EMPLOYEES --------------------
    path('employees/', views.employees, name='employees'),
    path('employees/list/', views.employee_list, name='employee-list'),
    path('employees/search/', views.employee_search, name='employee-search'),
    path('employees/form/', views.employee_form, name='employee-form'),
    path('employees/remove/', views.employee_remove, name='employee-remove'),
]
