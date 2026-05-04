from django.db import models
from bizanalytic.logiflex.models import LogiFlexClient


class ConsultingLead(models.Model):
    name = models.CharField(max_length=200)
    email = models.EmailField()
    company = models.CharField(max_length=200, blank=True)
    lead_type = models.CharField(max_length=50)
    service = models.CharField(max_length=50)
    extra_json = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_contacted = models.BooleanField(default=False)
    notes = models.TextField(blank=True)

    class Meta:
        verbose_name = "ConsultingLead"
        verbose_name_plural = "ConsultingLeads"
        permissions = (("manage_consultinglead", "Manage ConsultingLead"),)

    def __str__(self):
        return str(self.email)
