import random
from django.conf import settings
import requests
from bizanalytic.logiflex.models import LogEntry

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