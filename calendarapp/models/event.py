from datetime import datetime
from django.db import models
from django.urls import reverse

from calendarapp.models import EventAbstract
from accounts.models import User


class EventManager(models.Manager):
    def get_all_events(self, user):
        return Event.objects.filter(user=user, is_active=True, is_deleted=False)

    def get_running_events(self, user):
        return Event.objects.filter(
            user=user,
            is_active=True,
            is_deleted=False,
            data_interventie__gte=datetime.now().date(),
        ).order_by("data_interventie")

    def get_completed_events(self, user):
        return Event.objects.filter(
            user=user,
            is_active=True,
            is_deleted=False,
            status_live="finalizat"
    )


    def get_upcoming_events(self, user):
        return Event.objects.filter(
            user=user,
            is_active=True,
            is_deleted=False,
            data_interventie__gt=datetime.now().date(),
        )

    def get_pending_events(self, user):
        return Event.objects.filter(
            user=user,
            is_active=True,
            is_deleted=False,
            status="in_asteptare"      # doar cererile încă în aşteptare
        ).order_by("data_interventie")


class Operatie(models.Model):
    Nume = models.CharField(max_length=255)
    Laparoscopic = models.BooleanField(default=False)
    OperatieCurata = models.BooleanField(default=True)
    NecesitaIntubare = models.BooleanField(default=True)

    def __str__(self):
        return self.Nume


class Event(EventAbstract):
    STATUS_CHOICES = [
        ("in_asteptare", "În Așteptare"),
        ("aprobat", "Aprobat"),
        ("respins", "Respins"),
        ("finalizat", "Finalizat"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="events")
    nume_pacient = models.CharField(max_length=200, default="Pacient Necunoscut")
    tip_operatie = models.ForeignKey(Operatie, on_delete=models.CASCADE, null=True, related_name="evenimente")


    constrangeri_speciale = models.TextField(blank=True, null=True, default="Nicio constrângere")
    timp_estimare = models.IntegerField(default=60)
    data_interventie = models.DateTimeField(default=datetime.now)
    observatii = models.TextField(blank=True, null=True, default="Fără observații")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="in_asteptare")

    sala_alocata = models.CharField(max_length=20, blank=True, null=True, default="Nicio informatie")
    ora_inceput = models.TimeField(blank=True, null=True)
    ora_sfarsit = models.TimeField(blank=True, null=True)
    durata = models.IntegerField(blank=True, null=True)

    asistenta_alocata = models.ForeignKey(
    User,
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    related_name="interventii_asistate",
    limit_choices_to={"role": "assistant"},
    verbose_name="Asistentă alocată"
)   
    STATUS_REAL_CHOICES = [
    ("checked_in", "Checked-In"),
    ("anes_start", "Anestezie începută"),
    ("surgery_start", "Operație începută"),
    ("pacu", "PACU"),
    ("finalizat", "Finalizat"),
    ]

    status_live = models.CharField(
        max_length=20,
        choices=STATUS_REAL_CHOICES,
        default="checked_in",
        verbose_name="Stadiu Intervenție (Live)"
    )



    objects = EventManager()

    def __str__(self):
        return f"{self.nume_pacient} - {self.tip_operatie.Nume}"

    @property
    def get_html_url(self):
        url = reverse("calendarapp:event-detail", args=(self.id,))
        return f'<a href="{url}"> {self.nume_pacient} - {self.tip_operatie.Nume} </a>'

from django.contrib.auth import get_user_model

User = get_user_model()

class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notifications")
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Notificare pentru {self.user.username}: {self.message[:20]}"

from accounts.models import User  # asigură-te că există deja

class Pacient(models.Model):

    STATUS_CHOICES = [
        ("neprogramat", "Neprogramat"),
        ("in_asteptare", "În așteptare"),
        ("programat", "Programat"),
    ]
    nume_complet = models.CharField("Nume complet", max_length=200)
    cnp = models.CharField("CNP", max_length=13, unique=True)
    data_nasterii = models.DateField("Data nașterii")
    sex = models.CharField("Sex", max_length=1, choices=[("M", "Masculin"), ("F", "Feminin")])
    telefon = models.CharField("Telefon", max_length=20, blank=True, null=True)
    adresa = models.TextField("Adresă", blank=True, null=True)
    istoric_medical = models.TextField("Istoric medical", blank=True, null=True)
    chirurg = models.ForeignKey(User, on_delete=models.CASCADE, related_name="pacientii")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="neprogramat")     


    def __str__(self):
        return f"{self.nume_complet} ({self.cnp})"

