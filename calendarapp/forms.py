from django.forms import ModelForm, DateInput
from calendarapp.models import Event, EventMember
from django import forms


class EventForm(ModelForm):
    class Meta:
        model = Event
        fields = ["nume_pacient", "tip_operatie", "constrangeri_speciale", "timp_estimare", "data_interventie", "observatii"]
        
        widgets = {
            "nume_pacient": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Introduceți numele pacientului"}
            ),
            "tip_operatie": forms.Select(
                choices=[
                    ("curata", "Curată"),
                    ("murdara", "Murdară"),
                    ("laparoscopica", "Laparoscopică")
                ],
                attrs={"class": "form-control"}
            ),
            "constrangeri_speciale": forms.Textarea(
                attrs={"class": "form-control", "placeholder": "Introduceți eventuale constrângeri speciale"}
            ),
            "timp_estimare": forms.NumberInput(
                attrs={"class": "form-control", "placeholder": "Introduceți timpul estimat în minute"}
            ),
            
            "observatii": forms.Textarea(
                attrs={"class": "form-control", "placeholder": "Introduceți observații suplimentare"}
            ),
        }
        exclude = ["user"]

    def __init__(self, *args, **kwargs):
        super(EventForm, self).__init__(*args, **kwargs)
        self.fields["data_interventie"].input_formats = ("%Y-%m-%dT%H:%M",)



class AddMemberForm(forms.ModelForm):
    class Meta:
        model = EventMember
        fields = ["user"]
