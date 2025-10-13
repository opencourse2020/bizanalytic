# myapp/signals.py
from allauth.account.signals import email_confirmed
from django.dispatch import receiver
from .models import *
from bizanalytic.logiflex.utils.tools import generatecode
from bizanalytic.profiles.models import User

@receiver(email_confirmed)
def my_email_confirmed_handler(sender, request, email_address, **kwargs):
    # Access the confirmed email address:
    # print(f"Email confirmed: {email_address.email}")
    user = email_address.user
    logiclient = LogiFlexClient.objects.filter(email=email_address).first()

    if logiclient:
        logiclient.user = user
        logiclient.save()
        subscription = ServicePayment.objects.filter(client=logiclient).first()
        if subscription and subscription.lite_promotion_code:
            promotion_code = generatecode(8)
            subscription.advanced_promotion_code = promotion_code
            subscription.advanced_credits = 1
            subscription.save()
    else:
        logiclient = LogiFlexClient.objects.update_or_create(email=email_address, defaults={'user': user})


    if not user.is_active:
        user.is_active = True
        user.save()
        # print(f"User {user.username} activated after email confirmation.")