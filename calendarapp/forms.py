from django.forms import ModelForm, DateInput
from calendarapp.models import Event, EventMember
from django import forms
from calendarapp.models.event import Pacient  # sau doar `from .models import Pacient` dacă ai unificat

class PacientForm(forms.ModelForm):
    class Meta:
        model = Pacient
        exclude = ["chirurg"]
        labels = {
            "nume_complet": "Nume complet",
            "cnp": "CNP",
            "data_nasterii": "Data nașterii",
            "sex": "Sex",
            "telefon": "Telefon",
            "adresa": "Adresă",
            "istoric_medical": "Istoric medical",
        }

from django import forms
from django.forms import ModelForm
from calendarapp.models.event import Event, Pacient

from django import forms
from calendarapp.models.event import Event, Pacient

class EventForm(forms.ModelForm):
    pacient_selectat = forms.ModelChoiceField(
        queryset=Pacient.objects.none(),
        required=False,
        label="Alege pacientul",
        widget=forms.Select(attrs={"class": "form-control"})
    )

    class Meta:
        model = Event
        fields = [
            "nume_pacient",                  # completat automat
            "pacient_selectat",              # doar pentru selecție
            "tip_operatie",
            "constrangeri_speciale",
            "timp_estimare",
            "data_interventie",
            "observatii",
        ]
        exclude = ["user"]

        widgets = {
            "nume_pacient": forms.TextInput(attrs={"class": "form-control", "readonly": "readonly"}),
            "tip_operatie": forms.Select(attrs={"class": "form-control"}),
            "constrangeri_speciale": forms.Textarea(attrs={"class": "form-control"}),
            "timp_estimare": forms.NumberInput(attrs={"class": "form-control"}),
            "data_interventie": forms.TextInput(attrs={"class": "form-control", "readonly": "readonly"}),
            "observatii": forms.Textarea(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        self.fields["data_interventie"].input_formats = ("%Y-%m-%dT%H:%M",)

        if user:
            self.fields["pacient_selectat"].queryset = Pacient.objects.filter(chirurg=user)





class AddMemberForm(forms.ModelForm):
    class Meta:
        model = EventMember
        fields = ["user"]


class PacientForm(forms.ModelForm):
    class Meta:
        model = Pacient
        exclude = ["chirurg"]
        labels = {
            "nume_complet": "Nume complet",
            "cnp": "CNP",
            "data_nasterii": "Data nașterii",
            "sex": "Sex",
            "telefon": "Telefon",
            "adresa": "Adresă",
            "istoric_medical": "Istoric medical",
        }
        widgets = {
            "data_nasterii": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name != "data_nasterii":  # deja are clasa setată sus
                field.widget.attrs["class"] = "form-control"
            # adăugăm placeholders prietenoase
            placeholders = {
                "nume_complet": "ex: Ion Popescu",
                "cnp": "13 cifre",
                "telefon": "ex: 07xxxxxxxx",
                "adresa": "Strada, oraș, județ",
                "istoric_medical": "Detalii relevante (opțional)"
            }
            if name in placeholders:
                field.widget.attrs["placeholder"] = placeholders[name]
