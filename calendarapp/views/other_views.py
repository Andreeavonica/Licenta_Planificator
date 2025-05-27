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
        forms = self.form_class(user=request.user)
        status_filter = request.GET.get("status", "all")  # Preluăm filtrul din URL

        # 🔐 Filtrăm operațiile în funcție de rolul utilizatorului
        if request.user.role == "assistant":
            events = Event.objects.filter(
                asistenta_alocata=request.user,
                is_active=True,
                is_deleted=False
            )
        else:
            events = Event.objects.filter(
                user=request.user,
                is_active=True,
                is_deleted=False
            )

        if status_filter == "planificat":
            events = events.filter(status="aprobat")
        elif status_filter == "in_asteptare":
            events = events.filter(status="in_asteptare")

        # Filtrăm doar evenimentele aprobate programate în viitor (pentru events_month)
        if request.user.role == "assistant":
            events_month = Event.objects.filter(
                asistenta_alocata=request.user,
                is_active=True,
                is_deleted=False,
                status="aprobat",
                data_interventie__gte=datetime.now().date()
            ).order_by("data_interventie")
        else:
            events_month = Event.objects.filter(
                user=request.user,
                is_active=True,
                is_deleted=False,
                status="aprobat",
                data_interventie__gte=datetime.now().date()
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
                "start": f"{event.data_interventie.strftime('%Y-%m-%d')}T00:00:00",
                "status": event.get_status_display(),
                "sala_alocata": event.sala_alocata,
                "tip_operatie": tip_operatie,
                "constrangeri_speciale": event.constrangeri_speciale,
                "observatii": event.observatii,
                "nume_pacient": event.nume_pacient,
                "data_interventie": event.data_interventie.isoformat(),
                "chirurg": f"{event.user.first_name} {event.user.last_name}",
                "asistenta": f"{event.asistenta_alocata.first_name} {event.asistenta_alocata.last_name}" if event.asistenta_alocata else "Nespecificat",


            })

        notifications = []
        if request.user.is_authenticated:
            notifications = request.user.notifications.filter(is_read=False)[:5]

        context = {
            "form": forms,
            "events": event_list,
            "events_month": events_month,
            "status_filter": status_filter,
            "notifications": notifications,
        }
        return render(request, self.template_name, context)



    def post(self, request, *args, **kwargs):
        forms = self.form_class(request.POST, user=request.user)
        if forms.is_valid():
            form = forms.save(commit=False)
            form.user = request.user

            pacient = forms.cleaned_data.get("pacient_selectat")
            if pacient:
                form.nume_pacient = pacient.nume_complet
                pacient.status = "in_asteptare"
                pacient.save()

            form.save()
            return redirect("calendarapp:calendar")




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

from accounts.models import User  # asigură-te că ai importat User

@csrf_exempt
def confirm_schedule(request):
    if request.method == "POST":
        import json
        data = json.loads(request.body)

        for room in data.get("room_allocations", []):
            for surgery in room.get("schedule", []):
                if "start_time" not in surgery or "end_time" not in surgery:
                    continue

                try:
                    event = Event.objects.get(id=surgery["id"])

                    if event.status == "in_asteptare":
                        Notification.objects.create(
                            user=event.user,
                            message=f"Operația pentru pacientul {event.nume_pacient} a fost aprobată și programată."
                        )

                    # Timpul
                    start_parts = surgery["start_time"].split(":")
                    end_parts = surgery["end_time"].split(":")
                    ora_inceput = time(hour=int(start_parts[0]), minute=int(start_parts[1]))
                    ora_sfarsit = time(hour=int(end_parts[0]), minute=int(end_parts[1]))

                    durata = (
                        int(end_parts[0]) * 60 + int(end_parts[1])
                        - int(start_parts[0]) * 60 - int(start_parts[1])
                    )

                    # Salvare în event
                    event.ora_inceput = ora_inceput
                    event.ora_sfarsit = ora_sfarsit
                    event.durata = durata
                    event.sala_alocata = room["room"]
                    event.status = "aprobat"

                    # 💾 Salvăm asistenta dacă există în payload
                    nurse_id = surgery.get("nurse_id")
                    if nurse_id:
                        asistenta = User.objects.filter(id=nurse_id, role="assistant").first()
                        if asistenta:
                            event.asistenta_alocata = asistenta
                                    # ✅ Notificare pentru asistentă
                            Notification.objects.create(
                                user=asistenta,
                                message=f"Ai fost alocată la o intervenție în data de {event.data_interventie.strftime('%d.%m.%Y')}."
                            )


                    event.save()

                    # Update pacient
                    try:
                        pacient = Pacient.objects.get(nume_complet=event.nume_pacient, chirurg=event.user)
                        pacient.status = "programat"
                        pacient.save()
                    except Pacient.DoesNotExist:
                        pass

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


from calendarapp.models.event import Pacient
from calendarapp.forms import PacientForm
from django.contrib.auth.decorators import login_required





@csrf_exempt
@login_required
def ajax_adauga_pacient(request):
    if request.method == "POST":
        form = PacientForm(request.POST)
        if form.is_valid():
            pacient = form.save(commit=False)
            pacient.chirurg = request.user
            pacient.status = "neprogramat"  # 🔁 Setăm statusul automat
            pacient.save()
            return JsonResponse({
                "success": True,
                "pacient": {
                    "nume": pacient.nume_complet,
                    "cnp": pacient.cnp,
                    "nastere": pacient.data_nasterii.strftime("%Y-%m-%d"),
                    "sex": pacient.get_sex_display(),
                    "telefon": pacient.telefon,
                    "adresa": pacient.adresa,
                    "istoric": pacient.istoric_medical,
                    "status_display": pacient.get_status_display(),

                }
            })
        else:
            return JsonResponse({"success": False, "errors": form.errors})
    return JsonResponse({"success": False, "message": "Method not allowed"}, status=405)
@login_required
def pacienti_in_asteptare(request):
    events = Event.objects.filter(user=request.user, status="in_asteptare")
    enriched = []
    for e in events:
        pacient = Pacient.objects.filter(nume_complet=e.nume_pacient, chirurg=request.user).first()
        enriched.append({
            "event": e,
            "pacient": pacient
        })
    return render(request, "calendarapp/pacienti_list.html", {
        "pacienti": enriched,
        "tip": "asteptare"
    })

@login_required
def pacienti_programati(request):
    events = Event.objects.filter(user=request.user, status="aprobat")
    enriched = []
    for e in events:
        pacient = Pacient.objects.filter(nume_complet=e.nume_pacient, chirurg=request.user).first()
        enriched.append({
            "event": e,
            "pacient": pacient
        })
    return render(request, "calendarapp/pacienti_list.html", {
        "pacienti": enriched,
        "tip": "programati"
    })

from calendarapp.models.event import Pacient
from calendarapp.forms import PacientForm

def pacienti_neprogramati(request):
    pacienti = Pacient.objects.filter(chirurg=request.user, status="neprogramat")
    form = PacientForm()

    return render(request, "calendarapp/pacienti_list.html", {
        "pacienti": pacienti,
        "form": form,
        "tip": "neprogramati"
    })

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

@csrf_exempt
@login_required
def update_status(request, event_id):
    if request.method == "POST":
        event = get_object_or_404(Event, id=event_id)

        # Doar asistenta alocată poate modifica
        if request.user.role != "assistant" or event.asistenta_alocata != request.user:
            return JsonResponse({"error": "Acces nepermis"}, status=403)

        new_status = request.POST.get("status_live")

        if new_status in dict(Event.STATUS_REAL_CHOICES):
            event.status_live = new_status
            event.save()
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                "live_board",  # numele grupului definit în consumer
                {
                    "type": "send_status_update",   # corespunde metodei din consumer
                    "event_id": event.id,
                    "status_live": event.status_live,
                }
            )

            # (Vom adăuga aici emiterea WebSocket în pasul următor)
            return JsonResponse({"message": "Status actualizat cu succes"})
        else:
            return JsonResponse({"error": "Status invalid"}, status=400)
    return JsonResponse({"error": "Metodă invalidă"}, status=405)

@login_required
def evenimente_asistenta(request):
    if request.user.role != "assistant":
        return redirect("calendarapp:calendar")

    events = Event.objects.filter(
        asistenta_alocata=request.user,
        is_active=True,
        is_deleted=False,
        status="aprobat"
    ).order_by("data_interventie")

    return render(request, "calendarapp/events_list.html", {
        "object_list": events,
        "show_approved_fields": True
    })



from datetime import datetime, date
from typing import List, Dict

import numpy as np
from django.shortcuts import render
from django.contrib.auth.decorators import login_required

from calendarapp.optimization import schedule_surgeries, DAY_START, DAY_END, DIRTY_CLEAN_GAP

# ————————  UTILITARE  ————————

def _minutes_between(t1: str, t2: str) -> int:
    """Returnează numărul de minute dintre două timestamp‑uri HH:MM."""
    h1, m1 = map(int, t1.split(":"))
    h2, m2 = map(int, t2.split(":"))
    return (h2 * 60 + m2) - (h1 * 60 + m1)


def _compute_idle(room_schedule: List[Dict]) -> int:
    """Minutele idle într‑o sală între începutul zilei și ultima operație."""
    if not room_schedule:
        return 0
    idle = _minutes_between(f"{DAY_START//60:02d}:{DAY_START%60:02d}", room_schedule[0]["start_time"])
    for prev, cur in zip(room_schedule, room_schedule[1:]):
        idle += _minutes_between(prev["end_time"], cur["start_time"])
    return max(idle, 0)

# ————————  VIEW  ————————
from datetime import datetime, date
from typing import List, Dict
import numpy as np
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from calendarapp.optimization import schedule_surgeries, DAY_START, DAY_END, DIRTY_CLEAN_GAP


def _minutes_between(t1: str, t2: str) -> int:
    h1, m1 = map(int, t1.split(":"))
    h2, m2 = map(int, t2.split(":"))
    return (h2 * 60 + m2) - (h1 * 60 + m1)


def _compute_idle(room_schedule: List[Dict]) -> int:
    if not room_schedule:
        return 0
    idle = _minutes_between(f"{DAY_START//60:02d}:{DAY_START%60:02d}", room_schedule[0]["start_time"])
    for prev, cur in zip(room_schedule, room_schedule[1:]):
        idle += _minutes_between(prev["end_time"], cur["start_time"])
    return max(idle, 0)


@login_required
def manager_dashboard(request):
    """Vizualizare performantă a rezultatelor algoritmului de planificare."""
    date_str = request.GET.get("zi") or date.today().strftime("%Y-%m-%d")

    # 1️⃣  Rulează optimizarea pentru data selectată
    timetable = schedule_surgeries(date_str)

    # 2️⃣  KPI globale
    total_slots = (DAY_END - DAY_START) * (len(timetable) or 1)
    total_used = sum(r["total_used"] for r in timetable)
    schedule_eff = round(total_used / total_slots * 100, 1)
    unscheduled = sum(1 for r in timetable for e in r["schedule"] if e.get("unscheduled"))

    # 3️⃣  Structuri pentru grafice
    room_labels, room_util_pct = [], []
    asistenta_counts: Dict[str, int] = {}
    doctor_counts: Dict[str, int] = {}
    total_surgery_min = total_clean_min = idle_total = dirty_penalty = 0
    idle_per_room = []

    for row in timetable:
        # — sări peste sala de urgență / rezervă dacă așa e marcată
        if row.get("reserved_emergency"):
            continue

        # — utilizare sală
        room_labels.append(str(row["room"]))
        room_util_pct.append(round(row["total_used"] / (DAY_END - DAY_START) * 100, 1))
        util_pct = round(row["total_used"] / (DAY_END - DAY_START) * 100, 1)
        room_util_pct.append(util_pct)

        room_idle = _compute_idle(row["schedule"])
        idle_per_room.append(room_idle)
        idle_total += room_idle

        # — parcurge intervențiile din sală
        for ev in row["schedule"]:
            if ev.get("reserved"):
                continue
            total_surgery_min += ev["duration"]
            total_clean_min += ev["clean_time"]
            if not ev["is_clean"]:
                dirty_penalty += DIRTY_CLEAN_GAP

            # încărcare asistentă
            nurse = ev.get("nurse") or "—"
            asistenta_counts[nurse] = asistenta_counts.get(nurse, 0) + 1
            # încărcare doctor

            doctor = ev.get("doctor") or ev.get("surgeon") or "—"
            doctor_counts[doctor] = doctor_counts.get(doctor, 0) + 1

        idle_total += _compute_idle(row["schedule"])

    cost_labels = ["idle", "clean", "dirty"]
    cost_values = [idle_total, total_clean_min, dirty_penalty]

    # 4️⃣  Context pentru template
    context = {
        "selected_day": datetime.strptime(date_str, "%Y-%m-%d").date(),
        # KPI
        "total_surgeries": sum(len(r["schedule"]) for r in timetable),
        "schedule_efficiency": schedule_eff,
        "unscheduled_count": unscheduled,
        "avg_room_utilization": round(np.mean(room_util_pct) if room_util_pct else 0, 1),
        # Grafice
        "room_labels": room_labels,
        "room_util_pct": room_util_pct,
        "asistenta_labels": list(asistenta_counts.keys()),
        "asistenta_counts": list(asistenta_counts.values()),
        "doctor_labels": list(doctor_counts.keys()),
        "doctor_counts": list(doctor_counts.values()),
        "cost_labels": cost_labels,
        "cost_values": cost_values,
        "time_breakdown": [total_surgery_min, total_clean_min],
        "idle_labels": room_labels,
        "idle_values": idle_per_room,
    }

    return render(request, "calendarapp/dashboard.html", context)

@login_required
def asistenta_completed_events(request):
    if request.user.role != "assistant":
        return render(request, "403.html")  # sau redirect, în funcție de cum gestionezi permisiunile

    events = Event.objects.filter(
        asistenta_alocata=request.user,
        is_active=True,
        is_deleted=False,
        status_live="finalizat"
    ).order_by("data_interventie")

    context = {
        "object_list": events,
        "show_completed_fields": True
    }

    return render(request, "calendarapp/events_list.html", context)
from calendarapp.models.event import Pacient  # deja importat

@login_required
def pacientii_asistentei(request):
    if request.user.role != "assistant":
        return redirect("calendarapp:calendar")

    events = Event.objects.filter(
        asistenta_alocata=request.user,
        is_active=True,
        is_deleted=False
    )

    enriched = []
    for e in events:
        pacient = Pacient.objects.filter(
            nume_complet=e.nume_pacient,
            chirurg=e.user
        ).first()
        if pacient:
            enriched.append({
                "event": e,
                "pacient": pacient
            })

    return render(request, "calendarapp/pacienti_list.html", {
        "pacienti": enriched,
        "tip": "asistenta"
    })

@csrf_exempt
@login_required
def move_bulk_to_next_day(request):
    if request.method == "POST":
        data = json.loads(request.body)
        ids = data.get("ids", [])
        moved = 0

        for eid in ids:
            try:
                ev = Event.objects.get(id=eid)
                next_date = ev.data_interventie + timedelta(days=1)
                while next_date.weekday() >= 5:  # Sari sâmbătă/duminică
                    next_date += timedelta(days=1)
                ev.data_interventie = next_date
                ev.save()

                Notification.objects.create(
                    user=ev.user,
                    message=f"Operația pacientului {ev.nume_pacient} a fost mutată pentru {next_date.strftime('%d.%m.%Y')}."
                )
                moved += 1
            except Event.DoesNotExist:
                continue

        return JsonResponse({"message": f"{moved} operații mutate pentru ziua următoare."})

    return JsonResponse({"error": "Invalid method"}, status=405)
