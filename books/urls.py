from django.urls import path
from . import views

urlpatterns = [
    #------------------------- PATIENTS --------------------
    path('books/', views.books, name='books'),
    path('books/search/', views.books_search, name='books-search'),

    #path('books/print-tag/<int:books_id>/', views.books_print_tag, name='books-print-tag'),

    path('books/update-cache/', views.update_cache, name='books-update-cache'),
    path('books/update-cache-box/', views.update_cache_box, name='books-update-cache-box'),
]
