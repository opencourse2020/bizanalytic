import logging
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.core.mail import send_mail, EmailMultiAlternatives
from django.conf import settings
import os

# Initiate logger function
logger = logging.getLogger(__name__)

def sendemail(context):

    from_email = settings.EMAIL_HOST_USER  # Your email address
    subject = context.get('subject')
    to_email = context.get('to_email')
    company = context.get('company')
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
    html_content = 'Thank you for registering. Please find attached your Free Performance Analysis Report'
    template_name = "emails/email_template.html"
    context_data = {
        "clientname": company,
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
    print("attachments", file_path)
    # print("attachments name", attachments.name)
    # html_message = render_to_string(html_content, context)
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