
from django.shortcuts import render, redirect
from django.http import HttpResponseRedirect, JsonResponse
from django.views import generic
from django.utils.safestring import mark_safe
from datetime import timedelta, datetime, date
import calendar
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy, reverse
from django.shortcuts import get_object_or_404

from calendarapp.models import EventMember, Event
from calendarapp.utils import Calendar
from calendarapp.forms import EventForm, AddMemberForm

from django.views.decorators.csrf import csrf_exempt
from calendarapp.models import Event
from datetime import datetime, time

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json


from calendarapp.models.event import Notification  # adaugă în partea de importuri



def get_date(req_day):
    if req_day:
        year, month = (int(x) for x in req_day.split("-"))
        return date(year, month, day=1)
    return datetime.today()


def prev_month(d):
    first = d.replace(day=1)
    prev_month = first - timedelta(days=1)
    month = "month=" + str(prev_month.year) + "-" + str(prev_month.month)
    return month


def next_month(d):
    days_in_month = calendar.monthrange(d.year, d.month)[1]
    last = d.replace(day=days_in_month)
    next_month = last + timedelta(days=1)
    month = "month=" + str(next_month.year) + "-" + str(next_month.month)
    return month


class CalendarView(LoginRequiredMixin, generic.ListView):
    login_url = "accounts:signin"
    model = Event
    template_name = "calendar.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        d = get_date(self.request.GET.get("month", None))
        cal = Calendar(d.year, d.month)
        html_cal = cal.formatmonth(withyear=True)
        context["calendar"] = mark_safe(html_cal)
        context["prev_month"] = prev_month(d)
        context["next_month"] = next_month(d)
        return context


@login_required(login_url="signup")
def create_event(request):
    form = EventForm(request.POST or None)
    if request.POST and form.is_valid():
        nume_pacient = form.cleaned_data["nume_pacient"]
        tip_operatie = form.cleaned_data["tip_operatie"]
        constrangeri_speciale = form.cleaned_data["constrangeri_speciale"]
        timp_estimare = form.cleaned_data["timp_estimare"]
        data_interventie = form.cleaned_data["data_interventie"]
        observatii = form.cleaned_data["observatii"]

        Event.objects.create(
            user=request.user,
            nume_pacient=nume_pacient,
            tip_operatie=tip_operatie,
            constrangeri_speciale=constrangeri_speciale,
            timp_estimare=timp_estimare,
            data_interventie=data_interventie,
            observatii=observatii,
        )
        return HttpResponseRedirect(reverse("calendarapp:calendar"))
    return render(request, "event.html", {"form": form})


class EventEdit(generic.UpdateView):
    model = Event
    fields = ["nume_pacient", "tip_operatie", "constrangeri_speciale", "timp_estimare", "data_interventie", "observatii"]
    template_name = "event.html"


@login_required(login_url="signup")
def event_details(request, event_id):
    event = Event.objects.get(id=event_id)
    eventmember = EventMember.objects.filter(event=event)
    context = {"event": event, "eventmember": eventmember}
    return render(request, "event-details.html", context)


def add_eventmember(request, event_id):
    forms = AddMemberForm()
    if request.method == "POST":
        forms = AddMemberForm(request.POST)
        if forms.is_valid():
            member = EventMember.objects.filter(event=event_id)
            event = Event.objects.get(id=event_id)
            if member.count() <= 9:
                user = forms.cleaned_data["user"]
                EventMember.objects.create(event=event, user=user)
                return redirect("calendarapp:calendar")
            else:
                print("--------------User limit exceed!-----------------")
    context = {"form": forms}
    return render(request, "add_member.html", context)


class EventMemberDeleteView(generic.DeleteView):
    model = EventMember
    template_name = "event_delete.html"
    success_url = reverse_lazy("calendarapp:calendar")

from datetime import datetime  # Asigură-te că ai importat datetime

class CalendarViewNew(LoginRequiredMixin, generic.View):
    login_url = "accounts:signin"
    template_name = "calendarapp/calendar.html"
    form_class = EventForm

    def get(self, request, *args, **kwargs):
        forms = self.form_class()
        status_filter = request.GET.get("status", "all")  # Preluăm filtrul din URL

        # Obținem toate evenimentele în funcție de status
        events = Event.objects.filter(user=request.user, is_active=True, is_deleted=False)
        if status_filter == "planificat":
            events = events.filter(status="aprobat")
        elif status_filter == "in_asteptare":
            events = events.filter(status="in_asteptare")

        # Filtrăm doar evenimentele aprobate care sunt programate după data curentă
        events_month = Event.objects.filter(
            user=request.user,
            is_active=True,
            is_deleted=False,
            status="aprobat",  # Doar evenimente aprobate
            data_interventie__gte=datetime.now().date()  # Numai cele din viitor
        ).order_by("data_interventie")

        event_list = []
        
        for event in events.order_by("ora_inceput"):
            # Formatăm ora ca interval "HH:MM - HH:MM"
            if event.ora_inceput and event.ora_sfarsit:
                ora_formatata = f"{event.ora_inceput.strftime('%H:%M')} - {event.ora_sfarsit.strftime('%H:%M')}"
            else:
                ora_formatata = "Nespecificat"

            # Obținem numele operației
            tip_operatie = event.tip_operatie.Nume if event.tip_operatie else "Fără tip"

            # Titlul depinde de status
            if event.status == "in_asteptare":
                title = tip_operatie
            else:
                title = f"{ora_formatata} - {tip_operatie}"

            event_list.append({
                "id": event.id,
                "title": title,
                "start": f"{event.data_interventie.strftime('%Y-%m-%d')}T00:00:00",  # ora nefolosită în day view
                "status": event.get_status_display(),
                "sala_alocata": event.sala_alocata,
                "tip_operatie": tip_operatie,
                "constrangeri_speciale": event.constrangeri_speciale,
                "observatii": event.observatii,
                "nume_pacient": event.nume_pacient,
                "data_interventie": event.data_interventie.isoformat(),
            })



        print("DEBUG: Events Month", events_month)  # Verificăm în consolă
        notifications = []
        if request.user.is_authenticated:
            notifications = request.user.notifications.filter(is_read=False)[:5]
        context = {
            "form": forms,
            "events": event_list,
            "events_month": events_month,  # Transmitem events_month către calendar.html
            "status_filter": status_filter,
            "notifications": notifications  # adaugă aici

        }
        return render(request, self.template_name, context)



    def post(self, request, *args, **kwargs):
        forms = self.form_class(request.POST)
        if forms.is_valid():
            form = forms.save(commit=False)
            form.user = request.user
            form.save()
            return redirect("calendarapp:calendar")
        context = {"form": forms}
        return render(request, self.template_name, context)


def delete_event(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    if request.method == "POST":
        event.delete()
        return JsonResponse({"message": "Event successfully deleted."})
    else:
        return JsonResponse({"message": "Error!"}, status=400)


def next_week(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    if request.method == "POST":
        next_event = event
        next_event.id = None
        next_event.data_interventie += timedelta(days=7)
        next_event.save()
        return JsonResponse({"message": "Success!"})
    else:
        return JsonResponse({"message": "Error!"}, status=400)


def next_day(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    if request.method == "POST":
        next_event = event
        next_event.id = None
        next_event.data_interventie += timedelta(days=1)
        next_event.save()
        return JsonResponse({"message": "Success!"})
    else:
        return JsonResponse({"message": "Error!"}, status=400)
    


from calendarapp.optimization import schedule_surgeries

def run_schedule(request):
    selected_date = request.GET.get("date")
    if not selected_date:
        return JsonResponse({"error": "Nicio dată selectată"}, status=400)
    try:
        result = schedule_surgeries(selected_date)
        return JsonResponse({"room_allocations": result})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
    
def schedule_page(request):
    return render(request, "calendarapp/schedule.html")
@csrf_exempt
def confirm_schedule(request):
    if request.method == "POST":
        import json
        data = json.loads(request.body)

        for room in data.get("room_allocations", []):
            for surgery in room.get("schedule", []):
                try:
                    # Căutăm intervenția după nume
                    event = Event.objects.get(id=surgery["id"])
                    if event.status == "in_asteptare":
                        Notification.objects.create(
                            user=event.user,
                            message=f"Operația pentru pacientul {event.nume_pacient} a fost aprobată și programată."
                        )   
                    # Convertim ora_start / ora_sfarsit
                    start_parts = surgery["start_time"].split(":")
                    end_parts = surgery["end_time"].split(":")
                    ora_inceput = time(hour=int(start_parts[0]), minute=int(start_parts[1]))
                    ora_sfarsit = time(hour=int(end_parts[0]), minute=int(end_parts[1]))

                    # Calculăm durata în minute
                    durata = (int(end_parts[0]) * 60 + int(end_parts[1])) - (int(start_parts[0]) * 60 + int(start_parts[1]))

                    # Salvăm în event
                    event.ora_inceput = ora_inceput
                    event.ora_sfarsit = ora_sfarsit
                    event.durata = durata
                    event.sala_alocata = room["room"]

                    event.status = "aprobat"
                    event.save()

                except Event.DoesNotExist:
                    continue

        return JsonResponse({"message": "Planificarea a fost confirmată și salvată cu succes!"})
    else:
        return JsonResponse({"error": "Invalid request"}, status=400)
    
def schedule_page(request):
    time_labels = [
        "08", "08.5", "09", "09.5", "10", "10.5",
        "11", "11.5", "12", "12.5", "13", "13.5",
        "14", "14.5", "15", "15.5", "16", "16.5", "17"
    ]
    return render(request, "calendarapp/schedule.html", {
        "time_labels": time_labels,
        "today": date.today(), 

    })
@csrf_exempt
@csrf_exempt
def move_surgery(request):
    if request.method == "POST":
        data = json.loads(request.body)
        surgery_id = data.get("id")
        new_room = data.get("new_room")
        new_start = data.get("new_start_time")  # optional

        try:
            surgery = Event.objects.get(pk=surgery_id)
            surgery.sala_alocata = new_room
            if new_start:
                surgery.ora_inceput = new_start
            surgery.save()
            return JsonResponse({"message": "Operația a fost mutată."})
        except Event.DoesNotExist:
            return JsonResponse({"error": "Operația nu a fost găsită."}, status=404)

    # 🟡 Evităm return None pentru alte metode
    return JsonResponse({"error": "Method not allowed"}, status=405)

from django.contrib.auth.decorators import login_required
from calendarapp.models.event import Notification

@login_required
def mark_all_notifications_read(request):
    request.user.notifications.filter(is_read=False).update(is_read=True)
    return redirect("calendarapp:calendar")
