from django.shortcuts import render
from django.views.generic import (
    UpdateView,
    RedirectView,
    CreateView,
    View,
    TemplateView,
    DetailView,
    ListView,
    DeleteView,
)
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse, reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.http import JsonResponse

from . import models, forms
from bizanalytic.profiles.mixins import JsonFormMixin
# Create your views here.


class IndexView(TemplateView):
    template_name = "../templates/logiflex/home.html"


class NewsletterCreateView(UserPassesTestMixin, CreateView):
    model = models.NewsLetter_logiflex
    form_class = forms.NewsLetter_logiflexForm
    template_name = "logiflex/newsletter_logiflex_create.html"
    success_url = reverse_lazy("logiflex:newsletters:list")

    def test_func(self):
        return self.request.user.is_staff


class NewsletterEditView(UserPassesTestMixin, UpdateView):
    model = models.NewsLetter_logiflex
    form_class = forms.NewsLetter_logiflexForm
    template_name = "logiflex/newsletter_logiflex_create.html"
    success_url = reverse_lazy("logiflex:newsletters:list")

    def test_func(self):
        return self.request.user.is_staff


class NewsletterListView(UserPassesTestMixin, ListView):
    model = models.NewsLetter_logiflex
    template_name = "logiflex/newsletter_logiflex_list.html"

    def test_func(self):
        return self.request.user.is_staff


class NewsletterSubscriptionCreateView(CreateView, JsonFormMixin):
    def post(self, request, *args, **kwargs):
        cp_name = request.POST.get("cp_name").lower()
        email_nl = request.POST.get("em_nl").lower()
        subs = models.NewsLetter_logiflex_subscription.objects.filter(email=email_nl).first()
        company = subs.company


        if subs and cp_name==company.lower():
            message = _("Thank you for your request. This email is already registered with us")
        elif subs and not cp_name == company.lower():
            message = _("Thank you for your request. This email is already registered under different company name")
        else:
            message = _("Thank you for your request. You have been registered Successfully")
            subscription = models.NewsLetter_logiflex_subscription(email=email_nl, company=cp_name)
            subscription.save()
        data = {"submessage": message}

        return JsonResponse(data)

class NewsletterSubscriptionEditView(UserPassesTestMixin, UpdateView):
    model = models.NewsLetter_logiflex_subscription
    form_class = forms.NewsLetter_logiflex_subscriptionForm
    template_name = "logiflex/newsletter_logiflex_create.html"
    success_url = reverse_lazy("logiflex:newsletters:list")

    def test_func(self):
        return self.request.user.is_staff


class NewsletterSubscriptionListView(UserPassesTestMixin, ListView):
    model = models.NewsLetter_logiflex_subscription
    template_name = "logiflex/newsletter_logiflex_list.html"

    def test_func(self):
        return self.request.user.is_staff
