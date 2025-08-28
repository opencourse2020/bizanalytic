from django.contrib import admin
from . import models
# Register your models here.

model_objects = (models.Blog_logiflex,
                 models.NewsLetter_logiflex,
                 models.NewsLetter_logiflex_subscription,
                 models.LogiFlexClient,
                 models.LogiflexReport,
                 models.PricingPlan,
                 models.ServicePayment,
                 models.RequestedCall,
                 models.LogEntry,
                 models.PaymentsHistory
)

for m in model_objects:
    admin.site.register(m)