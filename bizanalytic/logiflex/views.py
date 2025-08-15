from django.shortcuts import render, redirect
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
from django.http import JsonResponse, HttpResponse
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, get_object_or_404
import json
import requests
import math
import pandas as pd
# Third party libraries
import stripe
from datetime import datetime, timedelta

from . import models, forms
from bizanalytic.profiles.mixins import JsonFormMixin
from bizanalytic.profiles.models import User
from .utils.mail import sendemail ,senduploadmail
from .utils.tools import generatecode
from .utils.call_llm import generate_analysis
from .utils.pre_process_datafile import test_validator
from .utils.local_analytics import *
# Create your views here.

# Initiate variables
stripe.api_key = settings.STRIPE_SECRET_KEY
stripe_price_id = settings.STRIPE_PRICE_ID
stripe_publishable = settings.STRIPE_PUBLISHABLE_KEY
stripe_webhook = settings.STRIPE_WEBHOOK_SECRET


class IndexView(TemplateView):
    template_name = "logiflex/home.html"


class RouteFileView(TemplateView):
    template_name = "logiflex/report_detail.html"
    def get_context_data(self, **kwargs):
        pu = self.kwargs.get("pk")
        report = models.LogiflexReport.objects.filter(pk=pu).first()
        log_message = models.LogEntry.objects.filter(report=report).first()
        if log_message.column_report:
            logcol = log_message.column_report.split("@@#@@")
        if log_message.date_report:
            logdate = log_message.date_report.split("@@#@@")
        if log_message.citi_report:
            logcity = log_message.citi_report.split("@@#@@")

        if report:
            kwargs["report"] = report
            kwargs["logcolumn"] = logcol
            kwargs["logdate"] = logdate
            kwargs["logcity"] = logcity
        else:
            kwargs["report"] = ""
            kwargs["logcolumn"] = ""
            kwargs["logdate"] = ""
            kwargs["logcity"] = ""
        return super(RouteFileView, self).get_context_data(**kwargs)


class ReportView(TemplateView):
    template_name = "logiflex/report_view.html"

    def get_context_data(self, **kwargs):
        pu = self.kwargs.get("pk")
        user = self.request.user

        report = models.LogiflexReport.objects.filter(client__user=user, pk=pu).first()
        if report:
            df = clean_data(report)
            df = calculate_kpis(df)
            carrier_stats = prepare_carrier_stats(df).reset_index()
            carrier_stats = json.loads(carrier_stats.to_json(orient='records'))
            # print("carrier stats")
            # print(carrier_stats.head(5))
            kwargs["carrierstats"] = carrier_stats
        return super(ReportView, self).get_context_data(**kwargs)


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "logiflex/dashboard.html"

    def get_context_data(self, **kwargs):
        pu = self.request.user
        reports = models.LogiflexReport.objects.filter(client__user=pu)
        total_reports = reports.count()
        if total_reports == 0:
            total_reports = 1

        ontime_reports = reports.filter(report_status="download")
        num_ontime_reports = ontime_reports.count()
        ontime_reports = ontime_reports.order_by('report_number')[:3]
        processing_reports = reports.filter(report_status="processing")
        num_processing_reports = processing_reports.count()
        processing_reports = processing_reports.order_by('report_number')[:3]
        canceled_reports = reports.filter(report_status="canceled")
        num_canceled_reports = canceled_reports.count()
        canceled_reports = canceled_reports.order_by('report_number')[:3]
        num_late_reports = reports.filter(expected_delivery__lt=datetime.now(), report_status="processing").count() + \
                       reports.filter(report_status="late").count()
        finished_reports = num_ontime_reports + num_late_reports
        late_reports = reports.filter(expected_delivery__lt=datetime.now(), report_status="processing").order_by('report_number')[:3]
        if finished_reports == 0:
            finished_reports = 1
        kwargs["latest_ontime_reports"] = num_ontime_reports
        kwargs["latest_processing_reports"] = num_processing_reports
        kwargs["latest_canceled_reports"] = num_canceled_reports
        kwargs["latest_late_reports"] = num_late_reports
        kwargs["ontime_reports"] = math.ceil((num_ontime_reports/total_reports)*100)
        kwargs["processing_reports"] = math.ceil((num_processing_reports/total_reports)*100)
        kwargs["canceled_reports"] = math.ceil((num_canceled_reports/total_reports)*100)
        kwargs["late_reports"] = math.ceil((num_late_reports/finished_reports)*100)
        return super(DashboardView, self).get_context_data(**kwargs)


class SampleAdvancedReportView(TemplateView):
    template_name = "logiflex/sample_report.html"


class AdvancedReportView(TemplateView):
    template_name = "logiflex/report.html"

    def get_context_data(self, **kwargs):
        pu = self.kwargs.get("pk")
        report = models.LogiflexReport.objects.filter(pk=pu).first()
        if report:
            kwargs["report"] = report.report_text
        return super(AdvancedReportView, self).get_context_data(**kwargs)


class NewsletterCreateView(UserPassesTestMixin, CreateView):
    model = models.NewsLetter_logiflex
    form_class = forms.NewsLetter_logiflexForm
    template_name = "logiflex/newsletter_logiflex_create.html"
    success_url = reverse_lazy("logiflex:newsletters:list")

    def test_func(self):
        return self.request.user.is_staff

    def get_context_data(self, **kwargs):
        kwargs["page_title"] = "Create NewsLetter"
        kwargs["title"] = "Newsletter"
        kwargs["pageheader1"] = "Edit a Newsletter"
        kwargs["pageheader2"] = "Add or Edit a New Logiflex Newsletter"
        kwargs["cardheader"] = "Newsletter Info"
        return super(NewsletterCreateView, self).get_context_data(**kwargs)


class NewsletterEditView(UserPassesTestMixin, UpdateView):
    model = models.NewsLetter_logiflex
    form_class = forms.NewsLetter_logiflexForm
    template_name = "logiflex/newsletter_logiflex_create.html"
    success_url = reverse_lazy("logiflex:newsletters:list")

    def test_func(self):
        return self.request.user.is_staff

    def get_context_data(self, **kwargs):
        kwargs["page_title"] = "Create NewsLetter"
        kwargs["title"] = "Newsletter"
        kwargs["pageheader1"] = "Edit a Newsletter"
        kwargs["pageheader2"] = "Add or Edit a New Logiflex Newsletter"
        kwargs["cardheader"] = "Newsletter Info"
        return super(NewsletterEditView, self).get_context_data(**kwargs)


class NewsletterListView(UserPassesTestMixin, ListView):
    model = models.NewsLetter_logiflex
    template_name = "logiflex/newsletter_logiflex_list.html"

    def test_func(self):
        return self.request.user.is_staff


class BlogCreateView(UserPassesTestMixin, CreateView):
    model = models.Blog_logiflex
    form_class = forms.Blog_logiflexForm
    template_name = "logiflex/newsletter_logiflex_create.html"
    success_url = reverse_lazy("logiflex:blog:list")

    def test_func(self):
        return self.request.user.is_staff

    def get_context_data(self, **kwargs):
        kwargs["page_title"] = "Create a Blog"
        kwargs["title"] = "Blog"
        kwargs["pageheader1"] = "Edit a Blog"
        kwargs["pageheader2"] = "Add or Edit a New Logiflex Blog"
        kwargs["cardheader"] = "Blog Info"
        return super(BlogCreateView, self).get_context_data(**kwargs)

class BlogEditView(UserPassesTestMixin, UpdateView):
    model = models.Blog_logiflex
    form_class = forms.Blog_logiflexForm
    template_name = "logiflex/newsletter_logiflex_create.html"
    success_url = reverse_lazy("logiflex:blog:list")

    def test_func(self):
        return self.request.user.is_staff

    def get_context_data(self, **kwargs):
        kwargs["page_title"] = "Create a Blog"
        kwargs["title"] = "Blog"
        kwargs["pageheader1"] = "Edit a Blog"
        kwargs["pageheader2"] = "Add or Edit a New Logiflex Blog"
        kwargs["cardheader"] = "Blog Info"
        return super(BlogEditView, self).get_context_data(**kwargs)


class BlogListView(UserPassesTestMixin, ListView):
    model = models.Blog_logiflex
    template_name = "logiflex/blogs_list.html"

    def test_func(self):
        return self.request.user.is_staff


class BlogDetailView(TemplateView):
    template_name = "logiflex/blog.html"

    def get_context_data(self, **kwargs):
        slug = self.kwargs.get("slug")
        blog = models.Blog_logiflex.objects.filter(slug=slug).first()

        # Retreive all blogs
        blogs = models.Blog_logiflex.objects.all()

        # Latest Blogs
        blogslatest = blogs.order_by('-date_created')[:3]
        categorytype = (
            ('logi_freight', _("Logistics & Freight")),
            # ('optimize', _("Optimization")),
            ('warehouse', _("Warehousing")),
            ('distribute', _("Delivery & Distribution")),
            ('driver', _("Drivers & Trucking")),
            ('cost', _("Cost Optimization")),
            # ('ai_insight', _("AI-Powered Insights")),
            ('predict', _("Forecasting & Predictions")),
        )
        # get the category title
        category_dict = dict(categorytype)
        search_term = blog.category
        result = (search_term, category_dict[search_term]) if search_term in category_dict else None

        # get the 3 related blogs
        relatedblog = blog.relatedblog.split("-")
        related_title1 = blogs.filter(pk=int(relatedblog[0])).first().anchor_title
        related_title2 = blogs.filter(pk=int(relatedblog[1])).first().anchor_title
        related_title3 = blogs.filter(pk=int(relatedblog[2])).first().anchor_title

        kwargs["title"] = blog.title
        kwargs["bodytop"] = blog.body
        kwargs["bodybottom"] = blog.body_bottom
        kwargs["datecreated"] = blog.date_created
        kwargs["picture"] = blog.picture
        kwargs["category"] = result[1] if result else None
        kwargs["meta_title"] = blog.meta_title
        kwargs["meta_description"] = blog.meta_description
        kwargs["insidepicture"] = blog.insidepicture
        kwargs["related1"] = blogs.filter(pk=int(relatedblog[0])).first().slug
        kwargs["related2"] = blogs.filter(pk=int(relatedblog[1])).first().slug
        kwargs["related3"] = blogs.filter(pk=int(relatedblog[2])).first().slug
        kwargs["related_title1"] = related_title1
        kwargs["related_title2"] = related_title2
        kwargs["related_title3"] = related_title3
        kwargs["blogs"] = blogslatest

        return super(BlogDetailView, self).get_context_data(**kwargs)


class BlogsView(TemplateView):
    template_name = "logiflex/blogs.html"

    def get_context_data(self, **kwargs):
        query = self.request.GET.get("cat")
        allblogs = models.Blog_logiflex.objects.all()

        if query:
            blogs = allblogs.filter(category=query)
        else:
            blogs = allblogs

        latestblogs = allblogs.order_by('-date_created')[:3]
        kwargs["blogs"] = blogs
        kwargs["latestblogs"] = latestblogs
        return super(BlogsView, self).get_context_data(**kwargs)


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
        client_nm = request.POST.get("client_nm")
        cp_name = request.POST.get("cp_nm")
        email_name = request.POST.get("email_nm")
        email_name = email_name.lower()
        route_file = request.FILES["route_file"]
        route_filename = route_file.name

        # Save client and result data
        user = User.objects.filter(email=email_name).first()

        if user:
            client = models.LogiFlexClient.objects.filter(user=user).first()
            if client:
                latest_report = models.LogiflexReport.objects.filter(client=client).order_by('-report_number').first()
                report = models.LogiflexReport(client=client, routefile=route_file, report_type="Free",
                                               report_number=latest_report.report_number+1)
                report.save()
            else:
                obj, created = models.LogiFlexClient.objects.update_or_create(email=email_name,
                                                                              defaults={'company': cp_name,
                                                                                        'user': user,
                                                                                        'contact_name': client_nm})

                report = models.LogiflexReport(client=obj, routefile=route_file, report_type="Free",
                                               report_number=1)
                report.save()
        else:
            client = models.LogiFlexClient.objects.filter(email=email_name).first()
            if client:
                latest_report = models.LogiflexReport.objects.filter(client=client).order_by('-report_number').first()
                report = models.LogiflexReport(client=client, routefile=route_file, report_type="Free",
                                               report_number=latest_report.report_number+1)
                report.save()
            else:
                obj, created = models.LogiFlexClient.objects.update_or_create(email=email_name,
                                                                              defaults={'company': cp_name,
                                                                                        'contact_name': client_nm})
                report = models.LogiflexReport(client=obj, routefile=route_file, report_type="Free", report_number=1)
                report.save()

        column_report, date_report, cities_report, routefilename = test_validator(route_file, report,
                                                                                  route_filename)

        # update route file
        # logireport.routefile = routefilename
        # logireport.save()

        # Save log data
        logiflex_log = models.LogEntry.objects.create(report=report, column_report=column_report,
                                                      date_report=date_report, citi_report=cities_report)

        # Send a confirmation Email to client
        email_info = {
            'subject': "Your Fleet Efficiency Report is in Progress 🚚📊",
            'to_email': [email_name, ],
            'client': client_nm,
            'report_list_link': "https://bizanalytic.com/logiflex/reports/list/",
            'cuurentyear': datetime.now().year
        }
        senduploadmail(email_info)

        message = "Report Uploaded Succssefully. Wait for a confirmation email from us."



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
        phone_nb = request.POST.get("phone_nb")

        client = models.LogiFlexClient.objects.filter(email=email_name).first()
        if client:
            if not client.contact_name:
                client.contact_name = client_name
            if not client.company:
                client.company = cp_name
            if not client.phone or not client.phone == phone_nb:
                client.phone = phone_nb
            client.save()
            call = models.RequestedCall(client=client)
            call.save()
            message = "Thank you for choosing BizAnalytic + LogiFlex to power your freight analytics. " \
                      "You will be contacted As Quick As Possible"

        data = {"submessage": message}

        return JsonResponse(data)


def create_checkout_sessions(request):

    if request.method == 'POST':
        try:

            # Create checkout session
            print("Start Stripe Session")
            print(settings.FRONTEND_SUCCESS_URL)
            session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price': stripe_price_id,
                    'quantity': 1,
                }],
                mode='payment',
                success_url=settings.FRONTEND_SUCCESS_URL + '?session_id={CHECKOUT_SESSION_ID}',
                cancel_url=settings.FRONTEND_CANCEL_URL,
                # customer_email=request.user.email if request.user.is_authenticated else None,
                # metadata={
                #     'user_id': request.user.id if request.user.is_authenticated else 'anonymous',
                #     'order_id': '141'
                # }
            )
            print("Session ID:", session.id)
            data = {"sessionId": session.id}
            return JsonResponse(data)

        except (ValueError, stripe.error.StripeError) as e:
            data = {'error': str(e)}
            return JsonResponse(data, status=400)


@login_required
def create_checkout_session(request, plan_id):
    plan = get_object_or_404(models.PricingPlan, id=plan_id)

    # Stripe Checkout Session
    session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        mode='subscription' if plan.name in ['monthly', 'quarterly'] else 'payment',
        line_items=[{
            'price': plan.stripe_price_id,
            'quantity': 1,
        }],
        customer_email=request.user.email,
        success_url=settings.FRONTEND_SUCCESS_URL + "?session_id={CHECKOUT_SESSION_ID}",
        cancel_url=settings.FRONTEND_CANCEL_URL,
    )

    # Save to DB
    subscription = models.ServicePayment.objects.create(
        client=request.user,
        plan=plan,
        stripe_checkout_id=session.id
    )

    return redirect(session.url)

class WebhookView(View):
    """Handles Stripe webhooks with signature verification"""

    @csrf_exempt
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        payload = request.body
        sig_header = request.META['HTTP_STRIPE_SIGNATURE']
        print("Payment Successful and WebHook initiated")
        try:
            # Verify webhook signature
            event = stripe.Webhook.construct_event(
                payload,
                sig_header,
                stripe_webhook
            )
        except ValueError as e:
            return HttpResponse(status=400)  # Invalid payload
        except stripe.error.SignatureVerificationError as e:
            return HttpResponse(status=401)  # Invalid signature

        # Handle specific events
        if event['type'] == 'checkout.session.completed':
            session = event['data']['object']
            self.handle_successful_payment(session)

        elif event['type'] == 'charge.refunded':
            self.handle_refund(event['data']['object'])
        # Add other event handlers as needed

        return HttpResponse(status=200)

    def handle_successful_payment(self, session):
        """Process completed payment"""
        try:
            # Retrieve and validate session data
            expanded_session = stripe.checkout.Session.retrieve(
                id=session.id,
                expand=['line_items', 'customer']
            )

            # Important: Reconcile with your database
            # user = self.request.user
            # print("User Email:", user.email)
            amount_paid = expanded_session.amount_total / 100  # Convert to currency
            if amount_paid == 49:
                reporttype = "onetime"
            elif amount_paid == 79:
                reporttype = "monthly"
            elif amount_paid == 199:
                reporttype = "quarter"
            email = expanded_session.customer_details.email
            email = email.lower()
            customer_name = expanded_session.customer_details.name
            phone_nb = expanded_session.customer_details.phone
            print(f"Payment was successful for session: {session['id']}")
            print(f"Name: {customer_name}")
            print(f"Email: {email}")
            print(f"Phone: {phone_nb}")
            print(f"Payment Amount: {amount_paid}")

            # check if client exists. if not it will be added
            client = models.LogiFlexClient.objects.filter(email=email).first()
            print("Client_email:", client.email)

            payment_plan = models.PricingPlan.objects.filter(price=amount_paid).first()
            if payment_plan:
                # Save payment and Create report instance with empty data
                servicepayment = models.ServicePayment.objects.filter(client=client).first()
                if servicepayment:
                    servicepayment.stripe_checkout_id = session['id']
                    servicepayment.service_type = payment_plan
                    servicepayment.is_active = True
                    servicepayment.save()
                else:
                    servicepayment = models.ServicePayment.objects.create(
                                        client=client,
                                        service_type=payment_plan,
                                        stripe_checkout_id=session['id'],
                                        is_active=True)

                servicepayment.reset_quota_if_needed()

                # downloadcode = generatecode(8)
                # report = models.LogiflexReport(client=client, payment=servicepayment, report_type='Paid',
                #                                download_code=downloadcode)
                # report.save()

            # print(session)


            # Implement your business logic:
            # - Update order status
            # - Grant access to service
            # - Send confirmation email

        except stripe.error.StripeError as e:
            # Handle error (log and retry mechanism)
            pass

    def handle_refund(self, charge):
        """Process refunds"""
        # Implement your refund logic
        pass


class Payment_PageView(TemplateView):
    template_name = "logiflex/stripe_pay.html"

    def get_context_data(self, **kwargs):
        if self.request.user.is_authenticated:
            logedin = 1
        else:
            logedin = 2
        kwargs["logedin"] = logedin
        # kwargs["stripe_publishable_key"] = stripe_publishable
        return super(Payment_PageView, self).get_context_data(**kwargs)


class Payment_SuccessView(LoginRequiredMixin, TemplateView):
    template_name = "logiflex/payment_success.html"

    def get_context_data(self, **kwargs):
        query = self.request.GET.get("cat")

        user = self.request.user
        servicepayment = models.ServicePayment.objects.filter(client__user=user).first()
        if servicepayment:
            if query:
                query = query.lower()
                if query in ["processing", "download", "canceled", "late"]:
                    reports = models.LogiflexReport.objects.filter(client__user=user, report_status=query)
                else:
                    reports = models.LogiflexReport.objects.filter(client__user=user)
            else:
                reports = models.LogiflexReport.objects.filter(client__user=user)
            # reports = reports.filter(report_created=True)
            kwargs["reports"] = reports.order_by('-report_number')
            if servicepayment.can_generate_report():
                kwargs["payid"] = servicepayment.pk
            else:
                kwargs["payid"] = "none"
        else:
            kwargs["reports"] = "none"
            kwargs["payid"] = "none"
        return super(Payment_SuccessView, self).get_context_data(**kwargs)


class FullReportView(LoginRequiredMixin, TemplateView):
    template_name = "logiflex/report_create.html"
    def get_context_data(self, **kwargs):
        pu = self.kwargs.get("pk")
        client = models.LogiFlexClient.objects.filter(user=self.request.user).first()
        servicepayment = models.ServicePayment.objects.filter(pk=pu, client=client).first()
        if servicepayment and servicepayment.can_generate_report():

            kwargs["contact_name"] = servicepayment.client.contact_name
            kwargs["company"] = servicepayment.client.company
            kwargs["email"] = servicepayment.client.email
            # kwargs["reportid"] = servicepayment.client.id

        return super(FullReportView, self).get_context_data(**kwargs)


class FullReportCreateView(LoginRequiredMixin, CreateView, JsonFormMixin):
    def post(self, request, *args, **kwargs):

        # load AJAX data from the template

        # clientid = request.POST.get("cixphoto")
        client_name = request.POST.get("client_nm")
        cp_name = request.POST.get("cp_nm")
        email_name = request.POST.get("email_nm")
        email_name = email_name.lower()
        route_file = request.FILES["route_file"]
        route_filename = route_file.name

        client = models.LogiFlexClient.objects.filter(user=self.request.user).first()
        servicepayment = models.ServicePayment.objects.filter(client=client).first()

        if servicepayment.can_generate_report():

            # Save client and result data
            user = self.request.user
            if not client.contact_name:
                client.contact_name = client_name
            if not client.company:
                client.company = cp_name

            client.save()

            downloadcode = generatecode(8)
            latest_report = models.LogiflexReport.objects.filter(client=client).order_by('-report_number').first()
            logireport = models.LogiflexReport.objects.create(client=client, payment=servicepayment,
                                                              download_code=downloadcode,
                                                              report_type='Paid',
                                                              report_number=latest_report.report_number+1)
            # add route file
            logireport.routefile = route_file
            # add report ID
            currentyear = datetime.now().year
            idl = "{:06d}".format(logireport.pk)
            logireport.report_id = f"RPT-{currentyear}-{idl}"
            # add expected_delivery
            logireport.expected_delivery = logireport.date_created + timedelta(days=1)

            logireport.save()

            # Clean and validate route file and generate logs
            column_report, date_report, cities_report, routefilename = test_validator(route_file, logireport, route_filename)


            # update route file
            # logireport.routefile = routefilename
            # logireport.save()

            # Save log data
            logiflex_log = models.LogEntry.objects.create(report=logireport, column_report=column_report,
                                                          date_report=date_report, citi_report=cities_report)

            # Send a confirmation Email to client
            email_info = {
                'subject': "Your Fleet Efficiency Report is in Progress 🚚📊",
                'to_email': [email_name, ],
                'client': client_name,
                'report_list_link': "https://bizanalytic.com/logiflex/reports/list/",
                'cuurentyear': datetime.now().year
            }
            senduploadmail(email_info)


            message = "Report Uploaded Succssefully. Wait for a confirmation email from us."
        else:
            message = "Report Already Uploaded Succssefully.Check the list of your reports for more details"

        data = {"submessage": message}

        return JsonResponse(data)


class Payment_FailView(TemplateView):
    template_name = "logiflex/payment_fail.html"


# def save_report_data(json_file_path):
#     # Load the JSON data
#     with open(json_file_path) as f:
#         data = json.load(f)
#
#     # Save Report Metadata
#     metadata = models.ReportMetadata.objects.create(
#         title=data['reportMetadata']['title'],
#         subtitle=data['reportMetadata']['subtitle'],
#         audience=data['reportMetadata']['audience'],
#         generated_date=data['reportMetadata']['generatedDate']
#     )
#
#     # Save Executive Summary
#     models.ExecutiveSummary.objects.create(
#         report_metadata=metadata,
#         primary_finding=data['executiveSummary']['primaryFinding'],
#         primary_recommendation=data['executiveSummary']['primaryRecommendation']
#     )
#
#     # Save Diagnostic Analysis
#     diagnostic_analysis = models.DiagnosticAnalysis.objects.create(
#         report_metadata=metadata,
#         carrier_matrix_description=data['diagnosticAnalysis']['carrierPerformanceMatrix']['description'],
#         bottleneck_title=data['diagnosticAnalysis']['bottleneckAnalysis']['title'],
#         bottleneck_description=data['diagnosticAnalysis']['bottleneckAnalysis']['description']
#     )
#
#     # Save Carriers
#     for carrier_data in data['diagnosticAnalysis']['carrierPerformanceMatrix']['carriers']:
#         models.Carrier.objects.create(
#             name=carrier_data['name'],
#             cost_per_mile=carrier_data['costPerMile'],
#             on_time_rate=carrier_data['onTimeRate'],
#             quadrant=carrier_data['quadrant']
#         )
#
#     # Save Bottleneck Findings
#     for finding_data in data['diagnosticAnalysis']['bottleneckAnalysis']['findings']:
#         models.BottleneckFinding.objects.create(
#             diagnostic_analysis=diagnostic_analysis,
#             title=finding_data['title'],
#             details=finding_data['details']
#         )
#
#     # Save Action Plans
#     for action_data in data['actionPlan']:
#         models.ActionPlan.objects.create(
#             report_metadata=metadata,
#             priority=action_data['priority'],
#             title=action_data['title'],
#             description=action_data['description'],
#             expected_outcome=action_data['expectedOutcome'],
#             estimated_impact=action_data['estimatedImpact'],
#             level_of_effort=action_data['levelOfEffort']
#         )
#
#     # Save Scenario Modeling
#     scenario_data = data['scenarioModeling']
#     models.ScenarioModeling.objects.create(
#         report_metadata=metadata,
#         carrier_shift_title=scenario_data['carrierShiftImpact']['title'],
#         carrier_shift_description=scenario_data['carrierShiftImpact']['description'],
#         new_delay_rate=scenario_data['carrierShiftImpact']['metrics']['newDelayRate'],
#         new_total_cost=scenario_data['carrierShiftImpact']['metrics']['newTotalCost'],
#         quarterly_savings=scenario_data['carrierShiftImpact']['metrics']['quarterlySavings'],
#         fuel_cost_title=scenario_data['fuelCostExposure']['title'],
#         fuel_cost_description=scenario_data['fuelCostExposure']['description'],
#         projected_cost_increase=scenario_data['fuelCostExposure']['metrics']['projectedCostIncrease']
#     )
#
#     return metadata
@csrf_exempt
def clean_csv(request):

    print("CSV Cleaning starts")
    # Proceed with OpenRefine cleaning
    if request.method == 'POST' and request.FILES["route_file"]:
        csv_file = request.FILES['route_file']
        df = pd.read_csv(request.FILES['route_file'])
        print(df.head(5))
        cleaned_csv = df
        print("cleaned_csv:", cleaned_csv)
        data = {"submessage": cleaned_csv}
        return JsonResponse(data)
    return JsonResponse({"error": "Invalid request"}, status=400)

