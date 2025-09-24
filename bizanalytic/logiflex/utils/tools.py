import random
from django.conf import settings
import requests
from bizanalytic.logiflex.models import LogEntry
from django.template.loader import render_to_string
from django.utils.html import strip_tags

def generatecode(length):
    result = ''
    characters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'
    characters_length = len(characters)
    counter = 0
    while counter < length:
        result += characters[random.randint(0, characters_length - 1)]
        counter += 1
    return result


def makenumericid(length):
    result = ''
    characters = '0123456789'
    characters_length = len(characters)
    counter = 0
    while counter < length:
        result += characters[random.randint(0, characters_length - 1)]
        counter += 1
    return result


# class DBHandler(logging.Handler):
#     def emit(self, record):
#         try:
#             LogEntry.objects.create(
#                 level=record.levelname,
#                 message=self.format(record),
#                 timestamp=record.created,
#                     # Add other relevant fields from record
#             )
#         except Exception:
#             pass # Handle database errors if necessary

# report_txt = generate_analysis(logireport)
#             # Create a report file and update report record
#             report_file = "done"
#             if report_file:
#                 logireport.report = report_file
#                 logireport.report_text = report_txt
#                 logireport.save()
#                 # report, report_created = models.LogiflexReport.objects.update_or_create(pk=reportid,
#                 #                                                                         defaults={'report': report_file,
#                 #                                                                                   'report_text': report_txt,
#                 #                                                                                   })
#             # Update payment reports
#             servicepayment.mark_report_used()
#
#             # Send Email to client
#             email_info = {
#                 'subject': "🚀 Your Logistics Performance Report is Here",
#                 'to_email': [email_name,],
#                 'company': cp_name,
#                 'client_name': client_name,
#                 'download_security_code'
#                 'shipments': "187",
#                 'avgdelivery': "2.3",
#                 'percent_change': 12,
#                 'ontimedelivery': 94,
#                 'delayreasons': "Top 3 Reasons",
#                 'suggested': "Route X, Carrier Y",
#                 'logiflex_contact': "Adam Akad",
#                 'phone': "+1 (832) 430-2434",
#                 'cc': [""],
#                 'bcc': [""],
#                 'attachments': logireport.routefile
#             }
#             sendemail(email_info)


def paymentconfirmation(context):

    from_email = settings.EMAIL_HOST_USER  # Your email address
    subject = context.get('subject')
    to_email = [context.get('to_email'),]
    context_data = {
        'portal_link': "https://bizanalytic.com/logiflex/payments/list/",
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
    template_name = "helpers/payment_confirmation.html"

    html_content = render_to_string(
        template_name=template_name,
        context=context_data
    )

    return html_content
