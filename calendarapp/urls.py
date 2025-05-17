
from django.urls import path

from . import views
from .views import other_views
from calendarapp.views.other_views import mark_all_notifications_read
from calendarapp.views.other_views import ajax_adauga_pacient, pacienti_in_asteptare, pacienti_programati,pacienti_neprogramati,update_status



app_name = "calendarapp"


urlpatterns = [
    path("calendar/", views.CalendarViewNew.as_view(), name="calendar"),
    path("calendars/", views.CalendarView.as_view(), name="calendars"),
    path('delete_event/<int:event_id>/', views.delete_event, name='delete_event'),
    path('next_week/<int:event_id>/', views.next_week, name='next_week'),
    path('next_day/<int:event_id>/', views.next_day, name='next_day'),
    path("event/new/", views.create_event, name="event_new"),
    path("event/edit/<int:pk>/", views.EventEdit.as_view(), name="event_edit"),
    path("event/<int:event_id>/details/", views.event_details, name="event-detail"),
    path(
        "add_eventmember/<int:event_id>", views.add_eventmember, name="add_eventmember"
    ),
    path(
        "event/<int:pk>/remove",
        views.EventMemberDeleteView.as_view(),
        name="remove_event",
    ),
    path("all-event-list/", views.AllEventsListView.as_view(), name="all_events"),
    path(
        "running-event-list/",
        views.RunningEventsListView.as_view(),
        name="running_events",
    ),
    path(
        "upcoming-event-list/",
        views.UpcomingEventsListView.as_view(),
        name="upcoming_events",
    ),
    path(
        "completed-event-list/",
        views.CompletedEventsListView.as_view(),
        name="completed_events",
    ),
     path(
        "pending-event-list/",
        views.PendingEventsListView.as_view(),
        name="pending_events",
    ),
    path("orar/", other_views.schedule_page, name="orar"),
    path("run-schedule/", other_views.run_schedule, name="run_schedule"),
    path("confirm-schedule/", other_views.confirm_schedule, name="confirm_schedule"),
    path("move-surgery/", other_views.move_surgery, name="move_surgery"),
    path("notifications/mark_all_read/", mark_all_notifications_read, name="mark_all_notifications_read"),
    path("pacienti/adauga/ajax/", ajax_adauga_pacient, name="ajax_adauga_pacient"),
    path("pacienti/in-asteptare/", pacienti_in_asteptare, name="pacienti_in_asteptare"),
    path("pacienti/programati/", pacienti_programati, name="pacienti_programati"),
    path("pacienti/neprogramati/", pacienti_neprogramati, name="pacienti_neprogramati"),
    path('update_status/<int:event_id>/', update_status, name='update_status'),










]
