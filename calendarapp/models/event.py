from datetime import datetime
from django.db import models
from django.urls import reverse

from calendarapp.models import EventAbstract
from accounts.models import User


class EventManager(models.Manager):
    """ Event manager """

    def get_all_events(self, user):
        return Event.objects.filter(user=user, is_active=True, is_deleted=False)

    def get_running_events(self, user):
        return Event.objects.filter(
            user=user,
            is_active=True,
            is_deleted=False,
            data_interventie__gte=datetime.now().date(),  # Folosim data_interventie
        ).order_by("data_interventie")

    def get_completed_events(self, user):
        return Event.objects.filter(
            user=user,
            is_active=True,
            is_deleted=False,
            data_interventie__lt=datetime.now().date(),
        )

    def get_upcoming_events(self, user):
        return Event.objects.filter(
            user=user,
            is_active=True,
            is_deleted=False,
            data_interventie__gt=datetime.now().date(),
        )


class Event(EventAbstract):
    """ Event model """
    STATUS_CHOICES = [
        ("in_asteptare", "În Așteptare"),
        ("aprobat", "Aprobat"),
        ("respins", "Respins"),
        ("finalizat", "Finalizat"),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="events")
    nume_pacient = models.CharField(max_length=200, default="Pacient Necunoscut")
    tip_operatie = models.CharField(
        max_length=50,
        choices=[
            ("curata", "Curată"),
            ("murdara", "Murdară"),
            ("laparoscopica", "Laparoscopică"),
        ],
        default="curata",
    )
    
    constrangeri_speciale = models.TextField(blank=True, null=True, default="Nicio constrângere")
    timp_estimare = models.IntegerField(default=60)
    data_interventie = models.DateTimeField(default=datetime.now)
    observatii = models.TextField(blank=True, null=True, default="Fără observații")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="in_asteptare")  # Nou status adăugat

    sala_alocata = models.CharField(max_length=20, blank=True, null=True, default="Nicio informatie")
    ora_inceput = models.TimeField(blank=True, null=True)
    ora_sfarsit = models.TimeField(blank=True, null=True)
    durata = models.IntegerField(blank=True, null=True)  




    objects = EventManager()

    def __str__(self):
        return f"{self.nume_pacient} - {self.tip_operatie}"

    @property
    def get_html_url(self):
        url = reverse("calendarapp:event-detail", args=(self.id,))
        return f'<a href="{url}"> {self.nume_pacient} - {self.tip_operatie} </a>'
