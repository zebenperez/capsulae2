from django.urls import path
from . import views


urlpatterns = [
    path('shifts/index/', views.index, name="shifts-index"),
    path('shifts/index/<int:user_id>/', views.index, name="shifts-index"),
    path('shifts/shift_calendar/', views.shift_calendar, name="shifts-shift-calendar"),
    path('shifts/calendar/', views.calendar, name="shifts-calendar"),
    path('shifts/get-shift/', views.get_shift, name="shifts-get-shift"),
    path('shifts/get-shift/<int:shift_id>/', views.get_shift, name="shifts-get-shift"),
    path('shifts/add-employee/', views.add_employee, name="shifts-add-employee"),
    path('shifts/remove-shift/<int:shift_id>/', views.remove_shift, name="shifts-remove-shift"),
    path('shifts/clone-shifts/', views.clone_shifts, name="shifts-clone-shifts"),

    path('shifts/check-updates/', views.check_updates, name="shifts-check-updates"),
    path('shifts/check-log/', views.check_log, name="shifts-check-log"),

    # ------------------------- JOURNEY ----------------------------------------
    path('shifts/journey-start/', views.journey_start, name="shifts-journey-start"),
    path('shifts/journey-end/', views.journey_end, name="shifts-journey-end"),
    path('shifts/journey-list/', views.journey_list, name="shifts-journey-list"),
    path('shifts/journey-stats/', views.journey_stats, name="shifts-journey-stats"),
]
