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
from django.http import JsonResponse, HttpResponse
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.views.decorators.csrf import csrf_exempt

# Third party libraries
import stripe

from . import models, forms
from bizanalytic.profiles.mixins import JsonFormMixin
from bizanalytic.profiles.models import User
from .utils.mail import sendemail
# Create your views here.

# Initiate variables
stripe.api_key = settings.STRIPE_SECRET_KEY
stripe_price_id = settings.STRIPE_PRICE_ID
stripe_publishable = settings.STRIPE_PUBLISHABLE_KEY
stripe_webhook = settings.STRIPE_WEBHOOK_SECRET

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
                report = models.LogiflexReport(client=client, routefile=route_file)
                report.save()
            else:
                obj, created = models.LogiFlexClient.objects.update_or_create(email=email_name,
                                                                              defaults={'company': cp_name,
                                                                                        'user': user,
                                                                                        'contact_name': client_nm})
                report = models.LogiflexReport(client=obj, routefile=route_file)
                report.save()
        else:
            client = models.LogiFlexClient.objects.filter(email=email_name).first()
            if client:
                report = models.LogiflexReport(client=client, routefile=route_file)
                report.save()
            else:
                obj, created = models.LogiFlexClient.objects.update_or_create(email=email_name,
                                                                              defaults={'company': cp_name,
                                                                                        'contact_name': client_nm})
                report = models.LogiflexReport(client=obj, routefile=route_file)
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


def create_checkout_session(request):

    if request.method == 'POST':
        try:
            # Validate input parameters
            # price_id = request.POST.get('price_id')
            # if not price_id:
            #     raise ValueError("Missing price ID")

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
            user_id = expanded_session.metadata.get('user_id')
            amount_paid = expanded_session.amount_total / 100  # Convert to currency
            print(f"Payment was successful for session: {session['id']}")
            print(f"User ID: {user_id}")
            print(f"Payment Amount: {amount_paid}")

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
        kwargs["stripe_publishable_key"] = stripe_publishable
        return super(Payment_PageView, self).get_context_data(**kwargs)


class Payment_SuccessView(TemplateView):
    template_name = "logiflex/payment_success.html"


class Payment_FailView(TemplateView):
    template_name = "logiflex/payment_fail.html"