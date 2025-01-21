from django.urls import path
#from . import views, donation_views
from . import views

urlpatterns = [
    path('signup/', views.signup, name='account-signup'),
    path('privacy-policy/', views.privacy_policy, name='privacy-policy'),
    path('send_new_password/<int:user_id>/', views.send_new_password, name='send_new_password'),
    path('send_new_password_by_email/', views.send_new_password_by_email, name='send_new_password_by_email'),
    path('activate_account/<slug:activation_key>/', views.activate_account, name='activate_account'),
    path('change_password/<int:user_id>/', views.change_password, name='change_password'),
    path('reactivate/<slug:activation_key>/', views.reactivate, name='reactivate'),

    #------------------------- PROFILE --------------------
    path('profile/view/', views.profile_view, name='profile-view'),
    path('profile/view/import/', views.profile_view_import, name='profile-view-import'),
    path('profile/view/import-farmatic/', views.profile_view_import_farmatic, name='profile-view-import-farmatic'),
    path('profile/view/dispensation-log/', views.profile_view_dispensation_log, name='profile-view-dispensation-log'),

    #------------------------- PAYMENTS --------------------
    path('payment-error/', views.payment_error, name='account-payment-error'),
    path('payment-send/<int:plan_id>/', views.payment_send, name='account-payment-send'),
    path('payment-stripe-error/', views.payment_stripe_error, name='account-payment-stripe-error'),
    path('payment-stripe-success/<slug:code>', views.payment_stripe_success, name='account-payment-stripe-success'),
    path('payment-stripe-verify/<slug:code>/', views.payment_stripe_verify, name='account-payment-stripe-verify'),

    #------------------------- EMPLOYEES --------------------
    path('employees/', views.employees, name='employees'),
    path('employees/list/', views.employee_list, name='employee-list'),
    path('employees/search/', views.employee_search, name='employee-search'),
    path('employees/form/', views.employee_form, name='employee-form'),
    path('employees/remove/', views.employee_remove, name='employee-remove'),
    path('employees/journeys/', views.employee_journeys, name='employee-journeys'),

    #------------------------- DONACIONES --------------------
    path('donations/', views.donations, name='donations'),
    path('donations/send/', views.donation_send, name='donation-send'),
    path('donation-custom/', views.donation_custom, name='donation-custom'),
    path('test/', views.test),

    #path('donations/index/', donation_views.donations_index, name='donation-index'),
    #path('donations/edit/', donation_views.donation_edit, name='donation-edit'),
    #path('donations/remove/', donation_views.donation_remove, name='donation-remove'),
    #path('donations/unique/', donation_views.donation_unique, name='donation-unique'),
    #path('donations/unique-send/', donation_views.donation_unique_send, name='donation-unique-send'),
]
