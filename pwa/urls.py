from django.urls import path
from pwa import views


urlpatterns = [
    path('', views.index, name="pwa-home"),
    path('home/', views.index, name="pwa-home"),
    path('login/<int:patient_id>/', views.pin_login, name="pwa-login"),
    path('login/', views.pin_login, name="pwa-login"),

    path('logoff/', views.pin_logout, name="pwa-logout"),

    # MANAGERS
    path('manager/', views.manager_home, name="pwa-manager"),
    path('manager/<int:patient_id>/', views.manager_home, name="pwa-manager"),

    # PATIENTS
    path('patient/<slug:patient>/', views.patient_home, name="pwa-patient"),
    path('patient/books/<slug:patient>/', views.patient_books, name="pwa-patient-books"),
    path('patient/books/print/<slug:patient>/<int:receipt_id>/', views.patient_books_print, name="pwa-patient-books-print"),
    path('patient/lopd/<slug:patient>/', views.patient_lopd, name="pwa-patient-lopd"),
]

