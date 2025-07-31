import logging
from django.template.loader import render_to_string
from django.core.mail import EmailMessage
from django.conf import settings


part1 = """
{% load static %}
{% load i18n %}
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Test Email</title>
</head>
<body>
<div class="main-container">
    <div class="container">
        <div class="header">
            <img src="https://idme.ma{% static "assets/logos/idmema-logo2.png" %}" width="100px" alt="idme.ma"> 
        </div>
        <div class="content">
            <p>"Thank you for registering. Please click the link below to confirm your email address" %}</p>
            <h6><a href="https://idme.ma/idme-apis/emailverification/"""


part2 = """/">Click Here</a> </h6>

            {% trans "For any question contact" %} <a href= "mailto:support@idme.ma">support@idme.ma</a>
        </div>
        <div class="footer">
            <p>{% trans "Thanks" %}</p>
        </div>
    </div>
</div>
</body>
</html>
"""

# Initiate logger function
logger = logging.getLogger(__name__)

def send_email(context):

    from_email = settings.EMAIL_HOST_USER  # Your email address
    subject = context.get('subject')
    to_email = context.get('to_email')
    cc = context.get('cc')
    bcc = context.get('bcc')
    attachments = context.get('attachments')
    html_content = 'Thank you for registering. Please find attached your Free Performance Analysis Report'

    if not to_email:
        raise ValueError("The 'to_email' address must be provided and cannot be empty.")
    elif not isinstance(to_email, list):
        to_email = [to_email]

    try:
        # html_message = render_to_string(html_content, context)
        message = EmailMessage(subject=subject, body=html_content, from_email=from_email, to=to_email, cc=cc, bcc=bcc,
                               )
        message.content_subtype = 'html'
        message.attach(attachments.name, attachments.read(), attachments.content_type)
        result = message.send()
        logger.info(f"Sending email to {', '.join(to_email)} with subject: {subject} - Status {result}")
    except Exception as e:
        logger.info(f"Sending email to {', '.join(to_email)} with subject: {subject} - Status 0")
        logger.exception(e)