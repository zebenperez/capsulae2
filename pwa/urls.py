from django.urls import path
from pwa import views


urlpatterns = [
    path('', views.index, name="pwa-home"),
    path('home/', views.index, name="pwa-home"),
    path('login/', views.pin_login, name="pwa-login"),
    path('login/<int:patient_id>/', views.pin_login, name="pwa-login"),
    path('logoff/', views.pin_logout, name="pwa-logout"),

    # MANAGERS
    path('manager/', views.manager_home, name="pwa-manager"),
    path('manager/<patient_id>/', views.manager_home, name="pwa-manager"),
]

