from django.urls import path
from . import views

urlpatterns = [
    #------------------------- PROJECTS --------------------
    path('projects/', views.projects, name='projects'),
    path('projects/list/', views.project_list, name='project-list'),
    path('projects/search/', views.project_search, name='project-search'),
    path('projects/new/', views.project_new, name='project-new'),
    path('projects/remove/', views.project_remove, name='project-remove'),

    #------------------------- PROJECT --------------------
    path('projects/view/<int:project_id>', views.project_view, name='project-view'),
    path('projects/form/', views.project_form, name='project-form'),

    path('projects/activities/', views.project_activities, name='project-activities'),
    path('projects/activity-form/', views.project_activity_form, name='project-activity-form'),
    path('projects/activity-remove/', views.project_activity_remove, name='project-activity-remove'),

    path('projects/budget/', views.project_budget, name='project-budget'),
    path('projects/income-form/', views.project_income_form, name='project-income-form'),
    path('projects/income-remove/', views.project_income_remove, name='project-income-remove'),
    path('projects/expense-form/', views.project_expense_form, name='project-expense-form'),
    path('projects/expense-remove/', views.project_expense_remove, name='project-expense-remove'),

    path('projects/drive/', views.project_drive, name='project-drive'),
    path('projects/drive/folder-form', views.project_folder_form, name='project-folder-form'),
    path('projects/drive/folder-remove', views.project_folder_remove, name='project-folder-remove'),
    path('projects/drive/folder-change', views.project_folder_change, name='project-folder-change'),
    path('projects/drive/file-list', views.project_file_list, name='project-file-list'),
    path('projects/drive/file-add', views.project_file_add, name='project-file-add'),
    path('projects/drive/file-form', views.project_file_form, name='project-file-form'),
    path('projects/drive/file-remove', views.project_file_remove, name='project-file-remove'),
    path('projects/drive/file-get/<int:obj_id>/', views.project_file_get, name='project-file-get'),
]
