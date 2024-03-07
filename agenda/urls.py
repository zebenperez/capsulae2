from django.urls import path
from . import views


urlpatterns = [
    path('notes/index/', views.index, name="notes-index"),
    path('notes/index/<int:user_id>/', views.index, name="notes-index"),
    path('notes/note_calendar/', views.note_calendar, name="notes-note-calendar"),
    path('notes/calendar/', views.calendar, name="notes-calendar"),
    path('notes/get-note/', views.get_note, name="notes-get-note"),
    path('notes/get-note/<int:note_id>/', views.get_note, name="notes-get-note"),
    path('notes/update-dates/', views.update_dates, name="notes-update-dates"),
    path('notes/create-note/<int:note_id>', views.create_note, name="notes-create-note"),
    path('notes/add-employee/', views.add_employee, name="notes-add-employee"),
    path('notes/remove-note/<int:note_id>/', views.remove_note, name="notes-remove-note"),
    #path('notes/clone-notes/', views.clone_notes, name="notes-clone-notes"),
    path('notes/list/', views.note_list, name="notes-list"),

    path('notes/file-list', views.file_list, name='note-file-list'),
    path('notes/file-add', views.file_add, name='note-file-add'),
    path('notes/file-form', views.file_form, name='note-file-form'),
    path('notes/file-remove', views.file_remove, name='note-file-remove'),
    #path('notes/file-get/<int:obj_id>/', views.file_get, name='note-file-get'),

    path('notes/check-log/', views.check_log, name="notes-check-log"),
]
