from django.contrib import admin
# from import_export import resources
# from import_export.admin import ImportExportModelAdmin
from . import models


# class TenantResource(resources.ModelResource):
#
#     class Meta:
#         model = models.Tenant
#
#
# class TenantAdmin(ImportExportModelAdmin):
#     resource_class = TenantResource



# class UserResource(resources.ModelResource):
#
#     class Meta:
#         model = models.User
#         exclude = ('last_login', 'date_joined',)


# class UserAdmin(ImportExportModelAdmin):
#     resource_class = UserResource


admin.site.register(models.User)

# admin.site.register(models.Tenant, TenantAdmin)




model_objects = (
    models.Admin,
    models.Member,
    models.Enterprise
    )

for m in model_objects:
    admin.site.register(m)
