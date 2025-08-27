from .models import *


def client_active(request):
    clientactive = False
    if request.user.is_authenticated and not request.user.is_staff:
        payment = ServicePayment.objects.filter(client__user=request.user).first()
        if payment:
            clientactive = payment.is_active
    return {'clientactive': clientactive}
