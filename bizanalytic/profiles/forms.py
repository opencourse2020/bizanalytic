from django import forms
from django.db import transaction
from django.forms.models import inlineformset_factory
from django.contrib.auth import get_user_model
from django.contrib.auth import forms as auth_forms
from django.contrib.auth.models import Permission, Group
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _
from allauth.account.forms import SignupForm, LoginForm, ResetPasswordForm
from . import models
# from captcha.fields import ReCaptchaField

User = get_user_model()


# 'class':"form-control form-control-lg bg-inverse bg-opacity-5"
class MyResetPasswordForm(ResetPasswordForm):
    # email_address = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-control form-control-lg bg-inverse bg-opacity-5'}))
    pass


class SignInForm(LoginForm):
    pass
#     captcha = ReCaptchaField()


class ProfileCreateForm(SignupForm):
    # USER_TYPES = [("parent", _("Parent")), ("student", _("Student")), ("professor", _("Professor")), ("institutadmin", _("Institute Admin")), ("serviceprovider", _("Service Provider"))]
    USER_TYPES = [("admin", _("Admin")), ("member", _("Member"))]
    user_type = forms.ChoiceField(choices=USER_TYPES, widget=forms.Select(attrs={'class': 'form-select form-select-lg bg-inverse bg-opacity-5'}))
    # captcha = ReCaptchaField()
    class Meta(auth_forms.UserCreationForm.Meta):
        model = User

    def save(self, request):
        with transaction.atomic():
            user = super().save(request)
            #***********************************************************************************************************
            #****************************************  Can be added in case we need more types of users ****************
            # ***********************************************************************************************************

            user_type = self.cleaned_data["user_type"]
            user_type_class_map = {
                "admin": models.Admin,
                "member": models.Member,

            }
            user_class = user_type_class_map[user_type]
            # ***********************************************************************************************************
            # ***********************************************************************************************************
            # ***********************************************************************************************************
            # user_type = "parent"
            # user_class = models.Parent
            profile = user_class()
            setattr(user, user_type, profile)
            user.is_staff = False
            if user_type == "admin":
                permissions = Permission.objects.filter(codename__startswith="manage")
                for perm in permissions:
                    user.user_permissions.add(perm)
                user.is_staff = True

            permission = get_object_or_404(
                Permission, codename=f"access_{user_type}_pages"
            )
            user.user_permissions.add(permission)

            group_name = f"{user_type}s".capitalize()
            group, created = Group.objects.get_or_create(name=group_name)
            user.groups.add(group)
            # user.date_expire = expire

            user.save()
            profile.save()
        return user


class UserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = [
            "first_name",
            "last_name",
        ]


class LanguageForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["language"]
        labels = {
            "language": _("Prefered Language")
        }


class EnterpriseForm(forms.ModelForm):
    class Meta:
        model = models.Enterprise
        fields = ["name"]
        labels = {
            "name": _("Name")
        }


class AdminForm(forms.ModelForm):
    class Meta:
        model = models.Admin
        fields = [
            "tel",
            "city",
            "country",
            "whatsapp",
            "address",
            "gender",
            # "yearofbirth",

        ]
        labels = {
            "tel": _("Telephone"),
            "whatsapp": _("Whatsapp Number"),
            "address": _("Address"),
            "city": _("City"),
            "country": _("Country"),
            "gender": _("Gender"),
            # "yearofbirth": _("Year of Birth")
        }


class RegularForm(forms.ModelForm):
    class Meta:
        model = models.Member
        fields = [
            "tel",
            "city",
            "country",
            "whatsapp",
            "address",
            # "picture",
            "gender",
            # "yearofbirth",

        ]
        labels = {
            "tel": _("Telephone"),
            "whatsapp": _("Whatsapp Number"),
            "address": _("Address"),
            "city": _("City"),
            "country": _("Country"),
            # "picture": _("Picture"),
            "gender": _("Gender"),
            # "yearofbirth": _("Year of Birth")
        }


AdminFormSet = inlineformset_factory(
    User, models.Admin, form=AdminForm, exclude=[], extra=1, can_delete=False,
)

RegularFormSet = inlineformset_factory(
    User, models.Member, form=RegularForm, exclude=[], extra=1, can_delete=False,
)


