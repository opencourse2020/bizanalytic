from django.utils.translation import gettext_lazy as _
from allauth.account.forms import LoginForm, SignupForm


def loginaccountform(request):
    return {'loginform': LoginForm()}


def signupaccountform(request):
    return {'signupform': SignupForm()}

