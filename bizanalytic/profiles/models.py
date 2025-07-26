from django.db import models
from django.conf import settings
from django.contrib.auth.models import AbstractUser
# from django.contrib.contenttypes.fields import GenericForeignKey
# from django.contrib.contenttypes.models import ContentType
from django.utils.translation import gettext_lazy as _
from guardian.mixins import GuardianUserMixin
from datetime import datetime, date, timedelta
# from .formatChecker import ContentTypeRestrictedFileField
import pytz
# from django.utils import timezone
from django_resized import ResizedImageField
# import geocoder
# from django.db.models import Q



def user_directory_path(instance, filename):
    # file will be uploaded to MEDIA_ROOT/user_<id>/<filename>
    return 'profile_pics/user_{0}/{1}'.format(instance.id, filename)

# def get_ipx():
#     g = geocoder.ip('me')
#     #     return g.ip
#
#     cc = 73
#
#     if g.lat and g.lat != 0 and g.lng != 0:
#         citya = City.objects.filter(Q(latitude_north__gte=g.lat) & Q(latitude_south__lte=g.lat) &
#                                            Q(longitude_east__gte=g.lng) & Q(longitude_west__lte=g.lng) &
#                                            Q(category_1__gt=0))
#
#         for cityaa in citya:
#             cc = cityaa.id
#
#     else:
#             cc = 73
#         #g.latlng
#     return cc


class User(GuardianUserMixin, AbstractUser):
    passchanged = models.BooleanField(default=False)
    language = models.CharField(max_length=10,
                                choices=settings.LANGUAGES,
                                default=settings.LANGUAGE_CODE)
    contacts_requests = models.PositiveIntegerField(default=0)
    prefered_city = models.SmallIntegerField(default=49)
    picture = ResizedImageField(size=[640, 480], upload_to=user_directory_path, blank=True, null=True)

    @property
    def profile(self):
        if hasattr(self, "member"):
            return self.member
        elif hasattr(self, "admin"):
            return self.admin
        else:
            return self

    @property
    def is_admin(self):
        return hasattr(self, "admin")

    @property
    def is_Member(self):
        return hasattr(self, "Member")



    class Meta(AbstractUser.Meta):
        permissions = (
            ("access_admin_pages", "Access Admin pages"),
            ("access_regular_pages", "Access Member user pages"),
        )


class Enterprise(models.Model):
    name = models.CharField(max_length=100)
    address = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=60, blank=True, null=True)
    country = models.CharField(max_length=60, blank=True, null=True)
    tel = models.CharField(max_length=20, blank=True, null=True)
    whatsapp = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(max_length=75, blank=True, null=True)
    dateadded = models.DateField(auto_now=True)

    class Meta:
        verbose_name = "Enterprise"
        verbose_name_plural = "Enterprises"
        # permissions = (("manage_enterprise", "Manage Enterprise"),)

    def __str__(self):
        return str(self.name)


class Profile(models.Model):
    gender_type = (
        ('F', _("Female")),
        ('M', _("Male")),
        ('U', _("Undisclosed")),
    )

    # YEARS = [(timezone.now().year - i, timezone.now().year - i) for i in range(90)]
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    enterprise = models.ForeignKey(Enterprise, on_delete=models.CASCADE, null=True)
    # picture1 = ResizedImageField(size=[640, 480], upload_to=user_directory_path, blank=True, null=True)
    # picture1 = ContentTypeRestrictedFileField(_("Profile picture"), upload_to=user_directory_path, default='user1.png',
    #                                          content_types=['image/bmp', 'image/gif', 'image/jpeg', 'image/png', ],
    #                                          max_upload_size=2621440, blank=True, null=True)
    address = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=60, blank=True, null=True)
    country = models.CharField(max_length=60, blank=True, null=True)
    tel = models.CharField(max_length=20)
    whatsapp = models.CharField(max_length=20, blank=True, null=True)
    dateadd = models.DateField(blank=True, null=True, default=datetime.now(tz=pytz.UTC))
    gender = models.CharField(max_length=1, choices=gender_type, null=True)
    # yearofbirth = models.SmallIntegerField(choices=YEARS, null=True)

    def __str__(self):
        if self.user.first_name:
            return "{} - {}".format(self.user.first_name, self.user.last_name)
        return self.user.username

    class Meta:
        abstract = True


class Admin(Profile):
    allow_comments = models.BooleanField(default=True)
    class Meta(Profile.Meta):
        verbose_name = "Admin"
        verbose_name_plural = "Admins"


class Member(Profile):
    allow_comments = models.BooleanField(default=True)

    class Meta(Profile.Meta):
        verbose_name = "Member"
        verbose_name_plural = "Members"

    # @property
    # def average_score(self):
    #     reviews = self.review_set.all()
    #     score = reviews.aggregate(models.Avg("score"))["score__avg"]
    #     return score


# class EnterpriseMember(models.Model):
#     member = models.ForeignKey(User, on_delete=models.CASCADE)
#     enterprise = models.ForeignKey(Enterprise, on_delete=models.CASCADE)
#     datajoined = models.DateField(auto_now=True)
#
#     objects = managers.EnterpriseManager()
#
#     class Meta:
#         verbose_name = "EnterpriseMember"
#         verbose_name_plural = "EnterpriseMembers"
#         permissions = (("manage_enterprisedata", "Manage Enterprise Data"),)
#
#     def __str__(self):
#         return str(self.member)


