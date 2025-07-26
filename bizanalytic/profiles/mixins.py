from django.contrib.auth.mixins import PermissionRequiredMixin
from django.http import JsonResponse
from django.urls import reverse_lazy


class JsonFormMixin:
    def form_valid(self, form):
        self.object = form.save()
        return JsonResponse(form.data)

    def form_invalid(self, form):
        data = {
            "success": False,
            "errors": {k: v[0] for k, v in form.errors.items()},
        }
        return JsonResponse(data, status=400)


class MemberRequiredMixin(PermissionRequiredMixin):
    permission_required = "profiles.access_member_pages"
    login_url = reverse_lazy("profiles:403")


class AdminRequiredMixin(PermissionRequiredMixin):
    permission_required = "profiles.access_admin_pages"
    login_url = reverse_lazy("profiles:403")


class AdminAllowedMixing(PermissionRequiredMixin):
    permission_required = ("", "", "", "", "")
    login_url = reverse_lazy("profiles:403")
