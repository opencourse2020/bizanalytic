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
# Third party libraries
import stripe

from . import models, forms
from bizanalytic.profiles.mixins import JsonFormMixin
from bizanalytic.profiles.models import User
from .utils.mail import sendemail
from .utils.tools import generatecode
from .utils.call_llm import generate_analysis

# Create your views here.

# Initiate variables
stripe.api_key = settings.STRIPE_SECRET_KEY
stripe_price_id = settings.STRIPE_PRICE_ID
stripe_publishable = settings.STRIPE_PUBLISHABLE_KEY
stripe_webhook = settings.STRIPE_WEBHOOK_SECRET

class IndexView(TemplateView):
    template_name = "logiflex/home.html"


class SampleAdvancedReportView(TemplateView):
    template_name = "logiflex/test.html"

    def get_context_data(self, **kwargs):

        kwargs["report"] = """### Executive Summary

**Estimated Quarterly Cost of Delays:**  
Based on our analysis of the logistics data for Mascaw, the estimated quarterly cost of delivery delays is approximately $150,000. This figure includes increased fuel costs, labor, and potential loss of business due to decreased customer satisfaction.

**Most Impactful Recommendation:**  
Our analysis indicates that optimizing carrier partnerships will yield the most significant improvement in operational margins. Specifically, shifting 50% of ABC Carriers' volume to GHI Transport, which has demonstrated higher reliability and lower cost per mile, is projected to reduce delay-related costs by approximately 20%.

---

### Diagnostic Analysis

**Root-Cause Analysis of 'Texas Triangle' Bottleneck:**

1. **Carrier-Specific Issues:**  
   - ABC Carriers has a higher incidence of delays, particularly on routes within the Texas Triangle. This suggests potential inefficiencies or capacity issues with this carrier.
   
2. **Time-of-Day Factors:**  
   - Analysis shows a higher frequency of delays during peak traffic hours, indicating that scheduling adjustments could mitigate some delays.

3. **Route-Specific Challenges:**  
   - Certain routes, particularly those involving Dallas and Houston, show consistent delays. Infrastructure or traffic congestion may be contributing factors.

**2x2 Matrix: Cost per Mile vs. On-Time Delivery %**

- **Strategic Partners:**  
  - GHI Transport: Low cost per mile and high on-time delivery percentage.
  
- **High-Risk Partners:**  
  - ABC Carriers: High cost per mile and low on-time delivery percentage.

---

### Prescriptive Action Plan

1. **Optimize Carrier Partnerships:**
   - **Expected Outcome:** Improved reliability and reduced costs.
   - **Estimated Impact:** 20% reduction in delay-related costs.
   - **Level of Effort:** Medium. Requires negotiation and potential contract adjustments.

2. **Adjust Scheduling to Avoid Peak Hours:**
   - **Expected Outcome:** Reduced delays during peak traffic times.
   - **Estimated Impact:** 10% improvement in on-time delivery.
   - **Level of Effort:** Low. Involves rescheduling existing routes.

3. **Route Optimization:**
   - **Expected Outcome:** More efficient routing to avoid congestion.
   - **Estimated Impact:** 5% reduction in fuel costs.
   - **Level of Effort:** High. Requires investment in route optimization software.

---

### Scenario Modeling & Future Outlook

1. **Impact of Shifting 50% of ABC Carriers' Volume to GHI Transport:**
   - **Expected Outcome:** Improved reliability and reduced costs.
   - **Estimated Impact:** 20% reduction in delay-related costs.
   - **Risk:** Potential capacity constraints with GHI Transport.

2. **Risk Exposure if Fuel Prices Increase by 10%:**
   - **Estimated Additional Cost:** Approximately $50,000 increase in quarterly fuel expenses.
   - **Mitigation Strategy:** Implement fuel-efficient driving practices and explore alternative fuel options.

---

This comprehensive analysis and action plan aim to enhance Mascaw's logistics operations by reducing hidden costs and improving reliability, ultimately leading to better operational margins without compromising customer trust."""
        return super(SampleAdvancedReportView, self).get_context_data(**kwargs)

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

        # Save client and result data
        user = User.objects.filter(email=email_name).first()
        if user:
            client = models.LogiFlexClient.objects.filter(user=user).first()
            if client:
                report = models.LogiflexReport(client=client, routefile=route_file, report_type="short")
                report.save()
            else:
                obj, created = models.LogiFlexClient.objects.update_or_create(email=email_name,
                                                                              defaults={'company': cp_name,
                                                                                        'user': user,
                                                                                        'contact_name': client_nm})
                report = models.LogiflexReport(client=obj, routefile=route_file, report_type="short")
                report.save()
        else:
            client = models.LogiFlexClient.objects.filter(email=email_name).first()
            if client:
                report = models.LogiflexReport(client=client, routefile=route_file, report_type="short")
                report.save()
            else:
                obj, created = models.LogiFlexClient.objects.update_or_create(email=email_name,
                                                                              defaults={'company': cp_name,
                                                                                        'contact_name': client_nm})
                report = models.LogiflexReport(client=obj, routefile=route_file, report_type="short")
                report.save()
        print("route file", report.routefile)
        # Create a report
        email_info = {
            'subject': "🚀 Your Monthly Logistics Performance Report is Here",
            'to_email': [email_name,],
            'company': cp_name,
            'client_name': client_nm,
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
            'attachments': report.routefile
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
                # report = models.LogiflexReport(client=client, payment=servicepayment, report_type='full',
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
        user = self.request.user
        servicepayment = models.ServicePayment.objects.filter(client__user=user).first()
        if servicepayment:
            reports = models.LogiflexReport.objects.filter(client__user=user)
            # reports = reports.filter(report_created=True)
            kwargs["reports"] = reports
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
        if servicepayment:
            downloadcode = generatecode(8)
            report = models.LogiflexReport(client=servicepayment.client, payment=servicepayment, report_type='full',
                                           download_code=downloadcode)
            report.save()
            kwargs["contact_name"] = report.client.contact_name
            kwargs["company"] = report.client.company
            kwargs["email"] = report.client.email
            kwargs["reportid"] = report.id
        return super(FullReportView, self).get_context_data(**kwargs)


class FullReportCreateView(LoginRequiredMixin, CreateView, JsonFormMixin):
    def post(self, request, *args, **kwargs):

        # load AJAX data from the template
        reportid = request.POST.get("cixphoto")
        client_name = request.POST.get("client_nm")
        cp_name = request.POST.get("cp_nm")
        email_name = request.POST.get("email_nm")
        email_name = email_name.lower()
        route_file = request.FILES["route_file"]

        print("report ID:", reportid)

        checkreport = models.LogiflexReport.objects.filter(pk=reportid).first()
        clientid= checkreport.client.id
        # client = models.LogiFlexClient.objects.filter(pk=)
        servicepayment = models.ServicePayment.objects.filter(client_id=clientid).first()

        if servicepayment.can_generate_report():

            # Save client and result data
            user = self.request.user
            client = models.LogiFlexClient.objects.filter(user=user).first()
            if not client.contact_name:
                client.contact_name = client_name
            if not client.company:
                client.company = cp_name

            client.save()

            # Update report info
            report, report_created = models.LogiflexReport.objects.update_or_create(pk=reportid,
                                                                                    defaults={'routefile': route_file})
            generate_analysis(report)
            # Create a report file and update report record
            report_file = "done"
            if report_file:
                report, report_created = models.LogiflexReport.objects.update_or_create(pk=reportid,
                                                                                        defaults={'report': report_file,
                                                                                                  'report_created': True})
            # Update payment reports
            servicepayment.mark_report_used()

            # Send Email to client
            email_info = {
                'subject': "🚀 Your Logistics Performance Report is Here",
                'to_email': [email_name,],
                'company': cp_name,
                'client_name': client_name,
                'download_security_code'
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
                'attachments': report.routefile
            }
            sendemail(email_info)
            message = "Report Created Succssefully. Wait for a confirmation email from us."
        else:
            message = "Report Already Created Succssefully.Check the list of your reports for more details"

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