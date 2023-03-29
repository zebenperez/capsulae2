from django.urls import path
from . import views

urlpatterns = [
    path('signup/', views.signup, name='account-signup'),
    path('privacy-policy/', views.privacy_policy, name='privacy-policy'),
]
