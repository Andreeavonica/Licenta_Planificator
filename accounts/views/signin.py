from django.views.generic import View
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from accounts.forms import SignInForm

class SignInView(View):
    """ User authentication view """

    template_name = "accounts/signin.html"
    form_class = SignInForm

    def get(self, request, *args, **kwargs):
        form = self.form_class()
        return render(request, self.template_name, {"form": form})

    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"]
            password = form.cleaned_data["password"]
            user = authenticate(email=email, password=password)
            if user:
                login(request, user)
                if user.role == "manager":
                    return redirect("manager_dashboard")  # Dashboard pentru manageri
                elif user.role == "surgeon":
                   return redirect("calendarapp:calendar") # Dashboard pentru chirurgi
                return redirect("patient_dashboard")  # Dashboard pentru pacienți
        return render(request, self.template_name, {"form": form})
