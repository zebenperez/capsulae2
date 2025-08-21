from django.contrib import admin
from .models import *

class BookAdmin(admin.ModelAdmin):
    list_display = ('isbn', 'title', 'subtitle', 'authors', 'serie', 'publisher_code', 'publisher_name')
    search_fields = ('isbn',)
admin.site.register(Book, BookAdmin)
