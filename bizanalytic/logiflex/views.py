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
from openai import OpenAI
# from . import models, forms
from .forms import *
from .models import *
from bizanalytic.profiles.mixins import JsonFormMixin
from bizanalytic.profiles.models import User
from .utils.mail import sendemail ,senduploadmail, sendapprovedreportmail
from .utils.tools import generatecode
from .utils.call_llm import generate_analysis
from .utils.pre_process_datafile import *
from .utils.local_analytics import *
from .utils.prompts import SYSTEM_PROMPT, JSON_SCHEMA
# Create your views here.

# Initiate variables
stripe.api_key = settings.STRIPE_SECRET_KEY
stripe_price_id = settings.STRIPE_PRICE_ID
stripe_publishable = settings.STRIPE_PUBLISHABLE_KEY
stripe_webhook = settings.STRIPE_WEBHOOK_SECRET
OPENAI_KEY = settings.OPENAI_KEY


client = OpenAI(api_key=OPENAI_KEY)


class IndexView(TemplateView):
    template_name = "logiflex/home.html"


class RouteFileView(TemplateView):
    template_name = "logiflex/report_detail.html"
    def get_context_data(self, **kwargs):
        pu = self.kwargs.get("pk")
        report = LogiflexReport.objects.filter(pk=pu).first()

        # load route file
        df = pd.read_csv(report.routefile)

        # Get route file information

        carriers = df['CarrierName'].unique()
        null_carriers = df['CarrierName'].isnull().sum()
        if null_carriers > 0:
            carriers_cleaned = df.dropna(subset=['CarrierName'])
            carriers = carriers_cleaned['CarrierName'].unique()

        drivers = df['DriverName'].unique()
        null_drivers = df['DriverName'].isnull().sum()
        if null_drivers > 0:
            drivers_cleaned = df.dropna(subset=['DriverName'])
            drivers = drivers_cleaned['DriverName'].unique()

        deliverystatus = df['DeliveryStatus'].unique()
        null_deliverystatus = df['DeliveryStatus'].isnull().sum()
        if null_deliverystatus > 0:
            deliverystatus_cleaned = df.dropna(subset=['DeliveryStatus'])
            deliverystatus = deliverystatus_cleaned['DeliveryStatus'].unique()

        distance_str, fuelcost_str, loadweight_str, deliveryhrs_str = process_route_info(df.describe())

        log_message = LogEntry.objects.filter(report=report).first()
        if log_message.column_report:
            logcol = log_message.column_report.split("@@#@@")
        if log_message.date_report:
            logdate = log_message.date_report.split("@@#@@")
        if log_message.citi_report:
            logcity = log_message.citi_report.split("@@#@@")

        # Report status percentage
        reportstatus = 50
        if report.report_text:
            reportstatus = 100
        elif report.report_status:
            reportstatus = 80

        if report:
            kwargs["report"] = report
            kwargs["reportstatus"] = reportstatus
            kwargs["logcolumn"] = logcol
            kwargs["logdate"] = logdate
            kwargs["logcity"] = logcity
            kwargs["carriers"] = carriers
            kwargs["null_carriers"] = null_carriers
            kwargs["drivers"] = drivers
            kwargs["null_drivers"] = null_drivers
            kwargs["deliverystatus"] = deliverystatus
            kwargs["null_deliverystatus"] = null_deliverystatus
            kwargs["distance_str"] = distance_str
            kwargs["fuelcost_str"] = fuelcost_str
            kwargs["loadweight_str"] = loadweight_str
            kwargs["deliveryhrs_str"] = deliveryhrs_str

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

        report = LogiflexReport.objects.filter(client__user=user, pk=pu).first()
        if report:
            dff = pd.read_csv(report.routefile)
            df = clean_data(dff)
            df = calculate_kpis(df)
            contingency_result = []
            if not report.contingency_result:
                results_df, worst_carrier = run_contingency_analysis(df)

                # to add to summary

                for idx, row in results_df.iterrows():
                    competitor = row['Competitor']
                    odds_ratio = row['Odds_Ratio']
                    p_value = row['P_Value']
                    contingency_result.append(
                        f"{competitor} is {odds_ratio:.2f}x to deliver on time than {worst_carrier}")
                report.contingency_result = contingency_result
                report.save()
            else:
                contingency_result = report.contingency_result

            carrier_stats = prepare_carrier_stats(df).reset_index()
            carrier_stats = json.loads(carrier_stats.to_json(orient='records'))
            q3 = df.groupby('CarrierName')['CostPerMile'].quantile(0.75).reset_index()
            q1 = df.groupby('CarrierName')['CostPerMile'].quantile(0.25).reset_index()
            median = df.groupby('CarrierName')['CostPerMile'].median().reset_index()
            q3m = q3['CostPerMile'] - median['CostPerMile']
            mq1 = median['CostPerMile'] - q1['CostPerMile']
            giqr = abs(q3m - mq1)
            hcar = q3.iloc[giqr.idxmax()]['CarrierName']
            lcar = q3.iloc[giqr.idxmin()]['CarrierName']
            hcarvar = f"<strong>{hcar}</strong> has the widest cost variance (high risk due to volatility)\n"
            hcarvar = hcarvar + f"(opportunity to negotiate consistent rates with <strong>{hcar}</strong>)"
            lcarvar = f"<strong>{lcar}</strong> has more consistent cost variance"

            iqr = q3['CostPerMile'] - q1['CostPerMile']
            # min_iqr = iqr.min()
            min_iqr_index = iqr.idxmin()
            lowiqr = q3.iloc[min_iqr_index]['CarrierName']
            lowiqrvar = f"If the goal is predictability & cost stability, <strong>{lowiqr}</strong> is the best candidate."
            cost_mile = df[['CarrierName', 'CostPerMile']]
            cost_mile = json.loads(cost_mile.to_json(orient='records'))
            print(cost_mile)
            # print("carrier stats")
            kwargs["costmile"] = cost_mile
            kwargs["carrierstats"] = carrier_stats
            kwargs["contigency"] = contingency_result
            kwargs["hcarvar"] = hcarvar
            kwargs["lcarvar"] = lcarvar
            kwargs["lowiqrvar"] = lowiqrvar
        return super(ReportView, self).get_context_data(**kwargs)


class ReportSummaryView(LoginRequiredMixin, TemplateView):
    template_name = "logiflex/report_template.html"

    def get_context_data(self, **kwargs):
        pu = self.kwargs.get("pk")
        user = self.request.user
        if user.is_staff:
            report = LogiflexReport.objects.filter(pk=pu).first()
        else:
            report = LogiflexReport.objects.filter(client__user=user, pk=pu).first()
            if not report.viewed:
                report.viewed = True
                report.save()

        if report:
            log = LogEntry.objects.filter(report=report).first()
            flags = json.dumps(log.flags, indent=2)
            if report.report_text:

                #
                # # run summary analysis
                # csv_text = read_csv_into_text_and_df(report.routefile)
                # # Compact summary for prompt to control tokens (use this instead of full CSV if large)
                # asynch_preprocess = run_LLM_analysis.delay(flags, pu)
                # raw = asynch_preprocess.get()
                #
                # # report.report_text = raw
                # # report.report_status = "download"
                # # report.save()

                raw = report.report_text
                data = json.loads(raw)
            # data = raw
            client_name = report.client.company
            markdown_report = data.get("markdown_report", "")
            summary_json = data.get("summary_json", {})
            print("client view", client_name)

        else:
            client_name = ""
            markdown_report = ""
            summary_json = ""

        kwargs["client_name"] = client_name
        kwargs["markdown_report"] = markdown_report
        kwargs["summary_json"] = summary_json
        return super(ReportSummaryView, self).get_context_data(**kwargs)


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "logiflex/dashboard.html"

    def get_context_data(self, **kwargs):
        pu = self.request.user
        reports = LogiflexReport.objects.filter(client__user=pu)
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
        new_reports = reports.filter(viewed=False, report_approved=True)
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
        kwargs["newreports"] = new_reports

        return super(DashboardView, self).get_context_data(**kwargs)


class SampleAdvancedReportView(TemplateView):
    template_name = "logiflex/sample_report.html"


class AdvancedReportView(TemplateView):
    template_name = "logiflex/report.html"

    def get_context_data(self, **kwargs):
        pu = self.kwargs.get("pk")
        report = LogiflexReport.objects.filter(pk=pu).first()
        if report:
            kwargs["report"] = report.report_text
        return super(AdvancedReportView, self).get_context_data(**kwargs)


class NewsletterCreateView(UserPassesTestMixin, CreateView):
    model = NewsLetter_logiflex
    form_class = NewsLetter_logiflexForm
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
    model = NewsLetter_logiflex
    form_class = NewsLetter_logiflexForm
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
    model = NewsLetter_logiflex
    template_name = "logiflex/newsletter_logiflex_list.html"

    def test_func(self):
        return self.request.user.is_staff


class BlogCreateView(UserPassesTestMixin, CreateView):
    model = Blog_logiflex
    form_class = Blog_logiflexForm
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
    model = Blog_logiflex
    form_class = Blog_logiflexForm
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
    model = Blog_logiflex
    template_name = "logiflex/blogs_list.html"

    def test_func(self):
        return self.request.user.is_staff


class BlogDetailView(TemplateView):
    template_name = "logiflex/blog.html"

    def get_context_data(self, **kwargs):
        slug = self.kwargs.get("slug")
        blog = Blog_logiflex.objects.filter(slug=slug).first()

        # Retreive all blogs
        blogs = Blog_logiflex.objects.all()

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
        allblogs = Blog_logiflex.objects.all()

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
        subs = NewsLetter_logiflex_subscription.objects.filter(email=email_nl).first()

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
            subscription = NewsLetter_logiflex_subscription(email=email_nl, company=cp_name, area=area)
            subscription.save()

        data = {"submessage": message}

        return JsonResponse(data)


class NewsletterSubscriptionEditView(UserPassesTestMixin, UpdateView):
    model = NewsLetter_logiflex_subscription
    form_class = NewsLetter_logiflex_subscriptionForm
    template_name = "logiflex/newslettersubscrib_logiflex_create.html"
    success_url = reverse_lazy("logiflex:newsletters:list")

    def test_func(self):
        return self.request.user.is_staff


class NewsletterSubscriptionListView(UserPassesTestMixin, ListView):
    model = NewsLetter_logiflex_subscription
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
            client = LogiFlexClient.objects.filter(user=user).first()
            if client:
                latest_report = LogiflexReport.objects.filter(client=client).order_by('-report_number').first()
                report = LogiflexReport(client=client, routefile=route_file, report_type="Free",
                                               report_number=latest_report.report_number+1)
                report.save()
            else:
                obj, created = LogiFlexClient.objects.update_or_create(email=email_name,
                                                                              defaults={'company': cp_name,
                                                                                        'user': user,
                                                                                        'contact_name': client_nm})

                report = LogiflexReport(client=obj, routefile=route_file, report_type="Free",
                                               report_number=1)
                report.save()
        else:
            client = LogiFlexClient.objects.filter(email=email_name).first()
            if client:
                latest_report = LogiflexReport.objects.filter(client=client).order_by('-report_number').first()
                report = LogiflexReport(client=client, routefile=route_file, report_type="Free",
                                               report_number=latest_report.report_number+1)
                report.save()
            else:
                obj, created = LogiFlexClient.objects.update_or_create(email=email_name,
                                                                              defaults={'company': cp_name,
                                                                                        'contact_name': client_nm})
                report = LogiflexReport(client=obj, routefile=route_file, report_type="Free", report_number=1)
                report.save()

        column_report, date_report, cities_report, routefilename = test_validator(report.pk,
                                                                                  route_filename)

        # update route file
        # logireport.routefile = routefilename
        # logireport.save()

        # Save log data
        logiflex_log = LogEntry.objects.create(report=report, column_report=column_report,
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

        client = LogiFlexClient.objects.filter(email=email_name).first()
        if client:
            if not client.contact_name:
                client.contact_name = client_name
            if not client.company:
                client.company = cp_name
            if not client.phone or not client.phone == phone_nb:
                client.phone = phone_nb
            client.save()
            call = RequestedCall(client=client)
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
    plan = get_object_or_404(PricingPlan, id=plan_id)

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
    subscription = ServicePayment.objects.create(
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
            client = LogiFlexClient.objects.filter(email=email).first()
            print("Client_email:", client.email)

            payment_plan = PricingPlan.objects.filter(price=amount_paid).first()
            if payment_plan:
                # Save payment and Create report instance with empty data
                servicepayment = ServicePayment.objects.filter(client=client).first()
                if servicepayment:
                    servicepayment.stripe_checkout_id = session['id']
                    servicepayment.service_type = payment_plan
                    servicepayment.is_active = True
                    servicepayment.save()
                else:
                    servicepayment = ServicePayment.objects.create(
                                        client=client,
                                        service_type=payment_plan,
                                        stripe_checkout_id=session['id'],
                                        is_active=True)

                servicepayment.reset_quota_if_needed()

                # downloadcode = generatecode(8)
                # report = LogiflexReport(client=client, payment=servicepayment, report_type='Paid',
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
        servicepayment = ServicePayment.objects.filter(client__user=user).first()
        if servicepayment:
            if query:
                query = query.lower()
                if query in ["processing", "download", "canceled", "late"]:
                    reports = LogiflexReport.objects.filter(client__user=user, report_status=query)
                else:
                    reports = LogiflexReport.objects.filter(client__user=user)
            else:
                reports = LogiflexReport.objects.filter(client__user=user)
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
        # pu = self.kwargs.get("pk")
        client = LogiFlexClient.objects.filter(user=self.request.user).first()

        servicepayment = ServicePayment.objects.filter(client=client).first()
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

        client = LogiFlexClient.objects.filter(user=self.request.user).first()
        servicepayment = ServicePayment.objects.filter(client=client).first()

        if servicepayment.can_generate_report():

            # Save client and result data
            user = self.request.user
            if not client.contact_name:
                client.contact_name = client_name
            if not client.company:
                client.company = cp_name

            client.save()

            downloadcode = generatecode(8)
            latest_report = LogiflexReport.objects.filter(client=client).order_by('-report_number').first()
            logireport = LogiflexReport.objects.create(client=client, payment=servicepayment,
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
            asynch_preprocess = test_validator.delay(logireport.pk, route_filename)
            flags = asynch_preprocess.get()
            # print("df columns after cleaning")
            # print(df.columns)
            # print(df.head(5))

            # Run local Analysis
            # summary = run_analysis(df)

            # Convert the summary array to json format to be stored as text in the database
            # json_string = json.dumps(summary)
            # logireport.report_summary = json_string
            # logireport.save()
            # update route file
            # logireport.routefile = routefilename
            # logireport.save()

            # Save log data
            # logiflex_log = LogEntry.objects.create(report=logireport, column_report=column_report,
            #                                               date_report=date_report, citi_report=cities_report, flags=flags)

            # Send a confirmation Email to client
            email_info = {
                'subject': _("Your Fleet Efficiency Report is in Progress 🚚📊"),
                'to_email': [email_name, ],
                'client': client_name,
                'report_list_link': "https://bizanalytic.com/logiflex/reports/list/",
                'cuurentyear': datetime.now().year
            }
            senduploadmail.delay(email_info)


            message = _("Report Uploaded Succssefully. Wait for a confirmation email from us.")
        else:
            message = _("Report Already Uploaded Succssefully.Check the list of your reports for more details")

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
#     metadata = ReportMetadata.objects.create(
#         title=data['reportMetadata']['title'],
#         subtitle=data['reportMetadata']['subtitle'],
#         audience=data['reportMetadata']['audience'],
#         generated_date=data['reportMetadata']['generatedDate']
#     )
#
#     # Save Executive Summary
#     ExecutiveSummary.objects.create(
#         report_metadata=metadata,
#         primary_finding=data['executiveSummary']['primaryFinding'],
#         primary_recommendation=data['executiveSummary']['primaryRecommendation']
#     )
#
#     # Save Diagnostic Analysis
#     diagnostic_analysis = DiagnosticAnalysis.objects.create(
#         report_metadata=metadata,
#         carrier_matrix_description=data['diagnosticAnalysis']['carrierPerformanceMatrix']['description'],
#         bottleneck_title=data['diagnosticAnalysis']['bottleneckAnalysis']['title'],
#         bottleneck_description=data['diagnosticAnalysis']['bottleneckAnalysis']['description']
#     )
#
#     # Save Carriers
#     for carrier_data in data['diagnosticAnalysis']['carrierPerformanceMatrix']['carriers']:
#         Carrier.objects.create(
#             name=carrier_data['name'],
#             cost_per_mile=carrier_data['costPerMile'],
#             on_time_rate=carrier_data['onTimeRate'],
#             quadrant=carrier_data['quadrant']
#         )
#
#     # Save Bottleneck Findings
#     for finding_data in data['diagnosticAnalysis']['bottleneckAnalysis']['findings']:
#         BottleneckFinding.objects.create(
#             diagnostic_analysis=diagnostic_analysis,
#             title=finding_data['title'],
#             details=finding_data['details']
#         )
#
#     # Save Action Plans
#     for action_data in data['actionPlan']:
#         ActionPlan.objects.create(
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
#     ScenarioModeling.objects.create(
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


class AdminReportsListView(UserPassesTestMixin, TemplateView):
    template_name = "logiflex/report_admin_list.html"

    def test_func(self):
        return self.request.user.is_staff

    def get_context_data(self, **kwargs):
        query = self.request.GET.get("cat")

        if query:
            query = query.lower()
            if query in ["processing", "late", "download", "canceled"]:
                reports = LogiflexReport.objects.filter(report_status=query)
            else:
                reports = LogiflexReport.objects.filter(report_approved=False, report_status__in=['processing', 'late'])
        else:
            reports = LogiflexReport.objects.filter(report_approved=False, report_status__in=['processing', 'late'])
        # reports = reports.filter(report_created=True)
        kwargs["reports"] = reports.order_by('-report_number')

        return super(AdminReportsListView, self).get_context_data(**kwargs)


class AdminApproveReportView(UserPassesTestMixin, CreateView, JsonFormMixin):
    def test_func(self):
        return self.request.user.is_staff

    def post(self, request, *args, **kwargs):
        reportid = int(request.POST.get("rx_cfr_ci"))
        print("Report ID: ", reportid)
        if reportid:
            report = LogiflexReport.objects.filter(pk=reportid).first()
            email_name = report.client.email
            client_name = report.client.contact_name
            company = report.client.company

            if not report.report_approved:
                report.report_approved = True
                report.report_date = datetime.now()
                report.report_status = "download"
                report.save()
                message = _("Report Approved Successfully")
                status = "success"
                raw = report.report_text
                data = json.loads(raw)
                summary_json = data.get("summary_json", {})
                # print(json.loads(summary_json))
                for kpi in summary_json:
                    if kpi == "kpis":
                        kpiss = summary_json[kpi]
                    else:
                        print(kpi)
                    # kpiss.append({"metric": kpi.metric, "value": kpi.value})

                # Send a confirmation Email to client
                email_info = {
                    'subject': _("Your Fleet Efficiency Report is Ready for your View 🚚📊"),
                    'to_email': [email_name, ],
                    'client': client_name,
                    'company': company,
                    'kpis': kpiss,
                    'report_list_link': "https://bizanalytic.com/logiflex/reports/list/",
                    'curentyear': datetime.now().year
                }
                sendapprovedreportmail.delay(email_info)

            else:
                message = _("Report Already Approved")
                status = "success"
        else:
            message = _("Report doesn't exist")
            status = "fail"

        data = {"submessage": message, "rpstatus": status}

        return JsonResponse(data)


class UpdateGasPricesView(UserPassesTestMixin, CreateView, JsonFormMixin):
    def test_func(self):
        return self.request.user.is_staff

    def post(self, request, *args, **kwargs):
        # us_cities = pd.read_csv(uscities_file)
        # us_states = pd.read_csv(ussates_file)
        state_gas_prices = pd.read_csv(gasprices_file)

        # city_instances = []
        # for index, row in us_cities.iterrows():
        #     c_instance = City(
        #         cityname=row['city'],
        #         state_name=row['state_name'],
        #         state_code=row['state'],
        #         # Map other columns to model fields
        #     )
        #     city_instances.append(c_instance)
        #
        # City.objects.bulk_create(city_instances)
        #
        # state_instances = []
        # for index, row in us_states.iterrows():
        #     s_instance = State(
        #         state_name=row['name'],
        #         state_code=row['code'],
        #         # Map other columns to model fields
        #     )
        #     state_instances.append(s_instance)
        #
        # State.objects.bulk_create(state_instances)

        gas_instances = []
        for index, row in state_gas_prices.iterrows():
            g_instance = GasPriceState(
                state_code=row['code'],
                premiumprice=row['Premium'],
                regularprice=row['Regular'],
                midgradeprice=row['Mid-Grade'],
                dieselprice=row['Diesel'],

                # Map other columns to model fields
            )
            gas_instances.append(g_instance)

        GasPriceState.objects.bulk_create(gas_instances)


        status = "success"
        message = "Data Added Successfully"
        data = {"submessage": message, "rpstatus": status}

        return JsonResponse(data)


class AboutUsView(TemplateView):
    template_name = "logiflex/aboutus.html"