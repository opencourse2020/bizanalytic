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
from bizanalytic.profiles.models import User
from .utils.mail import sendemail
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

        # load AJAX data from the template
        cp_name = request.POST.get("cp_name")
        if cp_name:
            cp_name = cp_name.lower()
        else:
            cp_name = "none"
        email_nl = request.POST.get("em_nl").lower()
        tp_area = int(request.POST.get("tp_area"))

        # Search the database for the email
        subs = models.NewsLetter_logiflex_subscription.objects.filter(email=email_nl).first()

        # Check if data exists or not in the database
        message = ""
        if subs:
            company = subs.company.lower()
            if company == "none":
                if cp_name == "none":
                    message = _("Thank you for your request. This email is already registered with us")
                else:
                    message = _("Thank you for your request. You have been registered Successfully")
                    area = ""
                    if tp_area == 1:
                        area = "lo"
                    elif tp_area == 2:
                        area = "ki"
                    subs.company = cp_name
                    subs.area = area
                    subs.save()
            else:
                if cp_name == "none" or not cp_name == company:
                    message = _("Thank you for your request. This email is already registered under different company name")
                elif cp_name == company:
                    message = _("Thank you for your request. This email is already registered with us")
        else:
            message = _("Thank you for your request. You have been registered Successfully")
            area = ""
            if tp_area == 1:
                area = "lo"
            elif tp_area == 2:
                area = "ki"
            subscription = models.NewsLetter_logiflex_subscription(email=email_nl, company=cp_name, area=area)
            subscription.save()

        data = {"submessage": message}

        return JsonResponse(data)


class NewsletterSubscriptionEditView(UserPassesTestMixin, UpdateView):
    model = models.NewsLetter_logiflex_subscription
    form_class = forms.NewsLetter_logiflex_subscriptionForm
    template_name = "logiflex/newslettersubscrib_logiflex_create.html"
    success_url = reverse_lazy("logiflex:newsletters:list")

    def test_func(self):
        return self.request.user.is_staff


class NewsletterSubscriptionListView(UserPassesTestMixin, ListView):
    model = models.NewsLetter_logiflex_subscription
    template_name = "logiflex/newslettersubscription_logiflex_list.html"

    def test_func(self):
        return self.request.user.is_staff


class SampleReportCreateView(CreateView, JsonFormMixin):
    def post(self, request, *args, **kwargs):

        # load AJAX data from the template
        cp_name = request.POST.get("cp_nm")
        email_name = request.POST.get("email_nm")
        email_name = email_name.lower()
        route_file = request.FILES["route_file"]

        # Save client and result data
        user = User.objects.filter(email=email_name).first()
        if user:
            client = models.LogiFlexClient.objects.filter(user=user).first()
            if client:
                report = models.LogiflexReport(client=client, routefile=route_file)
                report.save()
            else:
                obj, created = models.LogiFlexClient.objects.update_or_create(email=email_name,
                                                                              defaults={'company': cp_name,
                                                                                        'user': user})
                report = models.LogiflexReport(client=obj, routefile=route_file)
                report.save()
        else:
            client = models.LogiFlexClient.objects.filter(email=email_name).first()
            if client:
                report = models.LogiflexReport(client=client, routefile=route_file)
                report.save()
            else:
                obj, created = models.LogiFlexClient.objects.update_or_create(email=email_name,
                                                                              defaults={'company': cp_name})
                report = models.LogiflexReport(client=obj, routefile=route_file)
                report.save()
        print("route file", route_file)
        # Create a report
        email_info = {
            'subject': "🚀 Your Monthly Logistics Performance Report is Here",
            'to_email': [email_name,],
            'company': cp_name,
            'shipments': "187",
            'avgdelivery': "2.3",
            'percent_change': 12,
            'ontimedelivery': 94,
            'delayreasons': "Top 3 Reasons",
            'suggested': "Route X, Carrier Y",
            'logiflex_contact': "Adam Akad",
            'phone': "+1 (832) 430-2434",
            'cc': [""],
            'bcc': [""],
            'attachments': route_file
        }
        sendemail(email_info)
        message = "Report Created Succssefully"

        data = {"submessage": message}

        return JsonResponse(data)


class RequestCallView(TemplateView):
    template_name = "logiflex/call.html"


class BookACallView(CreateView, JsonFormMixin):
    def post(self, request, *args, **kwargs):
        message = ""
        cp_name = request.POST.get("cp_nm")
        client_name = request.POST.get("client_nm")
        email_name = request.POST.get("email_nm")
        email_name = email_name.lower()

        client = models.LogiFlexClient.objects.filter(email=email_name).first()
        if client:
            if not client.contact_name:
                client.contact_name = client_name
            if not client.company:
                client.company = cp_name
            client.save()
            call = models.RequestedCall(client=client)
            call.save()
            message = "Thank you for choosing BizAnalytic + LogiFlex to power your freight analytics. You will be contacted As Quick As Possible"

        data = {"submessage": message}

        return JsonResponse(data)