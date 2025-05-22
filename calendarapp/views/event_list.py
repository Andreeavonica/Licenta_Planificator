from django.views.generic import ListView

from calendarapp.models import Event


class AllEventsListView(ListView):
    """ All event list views """

    template_name = "calendarapp/events_list.html"
    model = Event

    def get_queryset(self):
        return Event.objects.get_all_events(user=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["show_all_fields"] = True
        return context



class RunningEventsListView(ListView):
    """ Running events list view """

    template_name = "calendarapp/events_list.html"
    model = Event

    def get_queryset(self):
        return Event.objects.get_running_events(user=self.request.user)

class UpcomingEventsListView(ListView):
    template_name = "calendarapp/events_list.html"
    model = Event

    def get_queryset(self):
        return Event.objects.filter(
            user=self.request.user,
            is_active=True,
            is_deleted=False,
            status="aprobat"
        ).order_by("data_interventie")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["show_approved_fields"] = True
        return context


    
class CompletedEventsListView(ListView):
    """ Completed events list view """

    template_name = "calendarapp/events_list.html"
    model = Event

    def get_queryset(self):
        return Event.objects.get_completed_events(user=self.request.user)
    
class PendingEventsListView(ListView):
    template_name = "calendarapp/events_list.html"
    model = Event

    def get_queryset(self):
        return Event.objects.get_pending_events(self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["show_pending_fields"] = True
        return context

class CompletedEventsListView(ListView):
    """ Completed events list view """

    template_name = "calendarapp/events_list.html"
    model = Event

    def get_queryset(self):
        return Event.objects.get_completed_events(user=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["show_completed_fields"] = True  # ← Adaugă asta
        return context
