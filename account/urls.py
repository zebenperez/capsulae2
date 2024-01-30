from django.urls import path
from . import views

urlpatterns = [
    path('signup/', views.signup, name='account-signup'),
    path('privacy-policy/', views.privacy_policy, name='privacy-policy'),
    path('send_new_password/<int:user_id>/', views.send_new_password, name='send_new_password'),
    path('send_new_password_by_email/', views.send_new_password_by_email, name='send_new_password_by_email'),
    path('activate_account/<slug:activation_key>/', views.activate_account, name='activate_account'),
    path('change_password/<int:user_id>/', views.change_password, name='change_password'),
    path('reactivate/<slug:activation_key>/', views.reactivate, name='reactivate'),


    #------------------------- EMPLOYEES --------------------
    path('employees/', views.employees, name='employees'),
    path('employees/list/', views.employee_list, name='employee-list'),
    path('employees/search/', views.employee_search, name='employee-search'),
    path('employees/form/', views.employee_form, name='employee-form'),
    path('employees/remove/', views.employee_remove, name='employee-remove'),
    path('employees/journeys/', views.employee_journeys, name='employee-journeys'),
]
