from django.http import HttpResponse, JsonResponse
from django.urls import reverse_lazy
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
# from django.utils import timezone
from django.utils.translation import gettext_lazy as _
# from django.shortcuts import get_object_or_404
# from django.contrib.auth.models import Permission, Group
from django.contrib.auth import get_user_model
from django.views.generic.detail import SingleObjectMixin
from django.contrib.auth.mixins import LoginRequiredMixin
# from django.contrib.auth.hashers import make_password
# from django.contrib import messages
# from django.core.exceptions import ValidationError
# from django.utils.text import slugify
from . import forms, models
from .mixins import (MemberRequiredMixin, AdminRequiredMixin, AdminAllowedMixing, JsonFormMixin)
# from datetime import datetime, date, timedelta
User = get_user_model()


class ProfileActivateView(AdminRequiredMixin, UpdateView):
    model = User
    fields = ["is_active"]
    template_name = "profiles/activate_form.html"
    formset_class = None
    success_url = reverse_lazy("profiles:profile")

    # def form_valid(self, form):
    #     pk = self.kwargs.get("pk")
    #     if self.request.user.pk==pk:
    #         form.save()
    #     else:
    #         raise ValidationError(_("You don't have authorization to make that change"))
    #     return super().form_valid(form)

    def get_context_data(self, **kwargs):

        kwargs["title"] = _("Deactivate your Account")

        return super().get_context_data(**kwargs)


class ProfilesUpdateView(LoginRequiredMixin, UpdateView):
    model = User
    fields = ["username", "first_name", "last_name", "picture"]
    template_name = "profiles/user_form.html"
    formset_class = None
    success_url = reverse_lazy("profiles:profile")

    # def form_valid(self, form):
    #     pk = self.kwargs.get("pk")
    #     if self.request.user.pk==pk:
    #         form.save()
    #     else:
    #         raise ValidationError(_("You don't have authorization to make that change"))
    #     return super().form_valid(form)
    def get_context_data(self, **kwargs):

        kwargs["title"] = _("Your Personal Info")

        return super().get_context_data(**kwargs)


class ProfileUpdateView(LoginRequiredMixin, UpdateView):
    model = User
    fields = ["email"]
    formset_class = None

    def get_object(self, queryset=None):
        return self.request.user

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context["formset"] = self.formset_class(
                self.request.POST, self.request.FILES, instance=self.object
            )
        else:
            context["formset"] = self.formset_class(instance=self.object)

        kwargs["title"] = _("Your Profile")

        return context

    def form_valid(self, form):
        context = self.get_context_data(form=form)
        formset = context["formset"]

        if formset.is_valid():
            response = super().form_valid(form)
            formset.instance = self.object
            formset.save()
            return response
        else:
            return super().form_invalid(form)


class LanguageUpdateView(LoginRequiredMixin, UpdateView):
    model = User
    form_class = forms.LanguageForm
    template_name = "profiles/language_form.html"
    success_url = reverse_lazy("profiles:profile")

    def get_context_data(self, **kwargs):

        kwargs["title"] = _("Language")

        return super().get_context_data(**kwargs)


class AdminUpdateView(AdminRequiredMixin, ProfileUpdateView):
    template_name = "profiles/profile_form.html"
    success_url = reverse_lazy("profiles:profile")
    formset_class = forms.AdminFormSet

    def get_context_data(self, **kwargs):

        kwargs["title"] = _("Your Profile")

        return super().get_context_data(**kwargs)

    # def get_form_kwargs(self):
    #     kwargs = super(ParentUpdateView, self).get_form_kwargs()
    #     year = 1930
    #     YEARS = [year + i for i in range(70)]
    #     kwargs.update({"yearofbirth": self.request.user.professor})
    #     return kwargs

class RegularUpdateView(MemberRequiredMixin, ProfileUpdateView):
    template_name = "profiles/profile_form.html"
    success_url = reverse_lazy("profiles:profile")
    formset_class = forms.RegularFormSet

    def get_context_data(self, **kwargs):

        kwargs["title"] = _("Your Profile")

        return super().get_context_data(**kwargs)


class ProfileDetailView(LoginRequiredMixin, TemplateView):
    template_name = "profiles/profile.html"


class ProfileView(LoginRequiredMixin, RedirectView):
    def get_redirect_url(self, *args, **kwargs):
        if hasattr(self.request.user, "admin"):
            return reverse_lazy("profiles:admin")
        elif hasattr(self.request.user, "member"):
            return reverse_lazy("profiles:member")

        return super().get_redirect_url(*args, **kwargs)


class DispatchLoginView(LoginRequiredMixin, RedirectView):
    def get_redirect_url(self, *args, **kwargs):
        if hasattr(self.request.user, "admin"):
            return reverse_lazy("coeanalytics:sdashboard")
        elif hasattr(self.request.user, "member"):
            return reverse_lazy("coeanalytics:sdashboard")
        else:
            return reverse_lazy("coeanalytics:sdashboard")

        return super().get_redirect_url(*args, **kwargs)


class ContactRequestView(SingleObjectMixin, View):
    model = models.User

    def post(self, *args, **kwargs):
        admin = self.get_object()
        admin.contacts_requests += 1
        admin.save()
        return HttpResponse()


class EnterpriseCreateView(LoginRequiredMixin, CreateView):
    model = models.Enterprise
    form_class = forms.EnterpriseForm
    template_name = "profiles/enterprise_edit.html"
    success_url = reverse_lazy("coeanalytics:analytics:edit")


class EnterpriseEditView(LoginRequiredMixin, CreateView):
    model = models.Enterprise
    form_class = forms.EnterpriseForm
    template_name = "profiles/enterprise_edit.html"
    success_url = reverse_lazy("coeanalytics:analytics:edit")


class UserDetailView(DetailView, SingleObjectMixin):
    model = models.User
    template_name = "profiles/user_detail.html"


class ForbiddenView(TemplateView):
    template_name = "../templates/403.html"


class ConditionsView(TemplateView):
    template_name = "../templates/conditions.html"


class PrivacyView(TemplateView):
    template_name = "../templates/privacy.html"
