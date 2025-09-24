import logging
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from datetime import datetime
import os
from celery import shared_task

# Initiate logger function
logger = logging.getLogger(__name__)

def sendemail(context):

    from_email = settings.EMAIL_HOST_USER  # Your email address
    subject = context.get('subject')
    to_email = context.get('to_email')
    company = context.get('company')
    client_name = context.get("client_name")
    cc = context.get('cc')
    bcc = context.get('bcc')
    shipments = context.get('shipments')
    avg_delivery = context.get('avgdelivery')
    percent_change = context.get('percent_change')
    ontime_delivery = context.get('ontimedelivery')
    delay_reasons = context.get('delayreasons')
    suggested = context.get('suggested')
    logiflex_contact = context.get('logiflex_contact')
    phone = context.get('phone')

    attachments = context.get('attachments')
    template_name = "emails/email_template.html"


    context_data = {
        "clientname": client_name,
        "shipments": shipments,
        "avg_delivery": avg_delivery,
        "percent_change": percent_change,
        "ontime_delivery": ontime_delivery,
        "delay_reasons": delay_reasons,
        "suggested": suggested,
        "logiflex_contact": logiflex_contact,
        "phone": phone

    }
    html_content = render_to_string(
        template_name=template_name,
        context=context_data
    )
    plain_message = strip_tags(html_content)

    if not to_email:
        raise ValueError("The 'to_email' address must be provided and cannot be empty.")
    elif not isinstance(to_email, list):
        to_email = [to_email]

    file_path = os.path.join(settings.BASE_DIR, "media", attachments.name)
    message = EmailMultiAlternatives(subject, plain_message, from_email, to_email)
    message.attach_alternative(html_content, "text/html")
    message.attach_file(file_path)
    # message.attach(attachments.name, attachments.read(), attachments.content_type)
    try:
        result = message.send()
        logger.info(f"Sending email to {', '.join(to_email)} with subject: {subject} - Status {result}")
    except Exception as e:
        logger.info(f"Sending email to {', '.join(to_email)} with subject: {subject} - Status 0")
        logger.exception(e)


@shared_task(name='email_upload_successful')
def senduploadmail(context):

    from_email = settings.EMAIL_HOST_USER  # Your email address
    subject = context.get('subject')
    to_email = context.get('to_email')

    context_data = {
    'dashboard_link' : context.get('report_list_link'),
    'client_name' : context.get('client'),
    'current_year' : context.get('cuurentyear'),
    }
    template_name = "emails/report_status.html"


    html_content = render_to_string(
        template_name=template_name,
        context=context_data
    )
    plain_message = strip_tags(html_content)

    if not to_email:
        raise ValueError("The 'to_email' address must be provided and cannot be empty.")
    elif not isinstance(to_email, list):
        to_email = [to_email]

    message = EmailMultiAlternatives(subject, plain_message, from_email, to_email, bcc=["bizanalytics.us@gmail.com", ])
    message.attach_alternative(html_content, "text/html")
    try:
        result = message.send()
        logger.info(f"Sending email to {', '.join(to_email)} with subject: {subject} - Status {result}")
    except Exception as e:
        logger.info(f"Sending email to {', '.join(to_email)} with subject: {subject} - Status 0")
        logger.exception(e)


@shared_task(name='email_approved')
def sendapprovedreportmail(context):

    from_email = settings.EMAIL_HOST_USER  # Your email address
    subject = context.get('subject')
    to_email = context.get('to_email')

    context_data = {
    'dashboard_link' : context.get('report_list_link'),
    'client_name' : context.get('client'),
    'company': context.get('company'),
    'current_year' : context.get('curentyear'),
    'kpis': context.get('kpis'),
    }
    template_name = "emails/email_template.html"
    print("Approved email will be sent ")

    html_content = render_to_string(
        template_name=template_name,
        context=context_data
    )
    plain_message = strip_tags(html_content)

    if not to_email:
        raise ValueError("The 'to_email' address must be provided and cannot be empty.")
    elif not isinstance(to_email, list):
        to_email = [to_email]

    message = EmailMultiAlternatives(subject, plain_message, from_email, to_email, bcc=["bizanalytics.us@gmail.com", ])
    message.attach_alternative(html_content, "text/html")
    try:
        result = message.send()
        logger.info(f"Sending email to {', '.join(to_email)} with subject: {subject} - Status {result}")
        print("Approved email sent successfully ")
    except Exception as e:
        logger.info(f"Sending email to {', '.join(to_email)} with subject: {subject} - Status 0")
        logger.exception(e)


@shared_task(name='email_approval_request')
def sendapprovalrequestmail(context):

    from_email = settings.EMAIL_HOST_USER  # Your email address
    subject = context.get('subject')
    to_email = context.get('to_email')

    context_data = {
    'dashboard_link' : context.get('report_list_link'),
    'client_name' : context.get('client'),
    'current_year' : context.get('cuurentyear'),
    }
    template_name = "emails/report_status.html"


    html_content = render_to_string(
        template_name=template_name,
        context=context_data
    )
    plain_message = strip_tags(html_content)

    if not to_email:
        raise ValueError("The 'to_email' address must be provided and cannot be empty.")
    elif not isinstance(to_email, list):
        to_email = [to_email]

    message = EmailMultiAlternatives(subject, plain_message, from_email, to_email)
    message.attach_alternative(html_content, "text/html")
    try:
        result = message.send()
        logger.info(f"Sending email to {', '.join(to_email)} with subject: {subject} - Status {result}")
    except Exception as e:
        logger.info(f"Sending email to {', '.join(to_email)} with subject: {subject} - Status 0")
        logger.exception(e)


@shared_task(name='email_newevent_notification')
def sendnotificationemail(context):

    from_email = settings.EMAIL_HOST_USER  # Your email address
    subject = context.get('subject')
    to_email = context.get('to_email')

    context_data = {
    'message' : context.get('message'),
    'client_name' : context.get('client'),
    'current_year' : context.get('cuurentyear'),
    'datecreated': datetime.now()
    }
    template_name = "emails/email_notification.html"

    html_content = render_to_string(
        template_name=template_name,
        context=context_data
    )
    plain_message = strip_tags(html_content)

    if not to_email:
        raise ValueError("The 'to_email' address must be provided and cannot be empty.")
    elif not isinstance(to_email, list):
        to_email = [to_email]

    message = EmailMultiAlternatives(subject, plain_message, from_email, to_email)
    message.attach_alternative(html_content, "text/html")
    try:
        result = message.send()
        logger.info(f"Sending email to {', '.join(to_email)} with subject: {subject} - Status {result}")
    except Exception as e:
        logger.info(f"Sending email to {', '.join(to_email)} with subject: {subject} - Status 0")
        logger.exception(e)


@shared_task(name='email_payment_confirmation')
def paymentconfirmationmail(context):

    from_email = settings.EMAIL_HOST_USER  # Your email address
    subject = context.get('subject')
    to_email = [context.get('to_email'),]
    print("to_email:", to_email)
    context_data = {
        'dashboard_link': context.get('report_list_link'),
        'customer_name': context.get('client'),
        'customer_company': context.get('company'),
        'customer_email': context.get('to_email'),
        'customer_address_line1': context.get('address_line1'),
        'customer_address_line2': context.get('address_line2'),
        'customer_city': context.get('city'),
        'customer_state': context.get('state'),
        'customer_zip': context.get('postal_code'),
        'customer_country': context.get('country'),
        'current_year': context.get('cuurentyear'),
        'receipt_number': context.get('receipt'),
        'receipt_date': context.get('payment_date'),
        'grand_total': context.get('amount_paid'),
        'company_name': "BizAnalytic",
        'operator_legal_name': "Adil Akaaboune",
        'company_address_line1': "The Woodlands",
        'company_address_line2': "Texas",
        'company_country': "United States of America",
        'support_email': "support@bizanalytic.com",
        'payment_brand': "Stripe",
        'refund_policy_url': "https://bizanalytic.com/refund-policy/",
        'desc': context.get('description'),
        'quantity': context.get('quantity'),
        'unit_price': context.get('unit_price'),
        'line_total': context.get('amount_paid'),
        'subtotal': context.get('amount_paid'),
    }
    template_name = "emails/payment_confirmation.html"

    html_content = render_to_string(
        template_name=template_name,
        context=context_data
    )
    plain_message = strip_tags(html_content)
    print(plain_message)
    if not to_email:
        raise ValueError("The 'to_email' address must be provided and cannot be empty.")
    elif not isinstance(to_email, list):
        to_email = [to_email]

    message = EmailMultiAlternatives(subject, plain_message, from_email, to_email,
                                     bcc=["support@bizanalytic.com", "bizanalytics.us@gmail.com"])
    message.attach_alternative(html_content, "text/html")
    try:
        result = message.send()
        print("result:", result)
        logger.info(f"Sending email to {', '.join(to_email)} with subject: {subject} - Status {result}")
    except Exception as e:
        print("Status 0", e)
        logger.info(f"Sending email to {', '.join(to_email)} with subject: {subject} - Status 0")
        logger.exception(e)