import datetime

from django.contrib import admin
from apps.home.models import ReferralUsers
from django.utils.translation import gettext_lazy as _


class ReferralFilter(admin.SimpleListFilter):
    title = 'Is referral' 
    parameter_name = 'is_referral'

    def lookups(self, request, model_admin):
        referral_users = [ru[0] for ru in ReferralUsers.objects.all().values_list('user__id')]
        users = []
        for user in model_admin.model.objects.all():
            if user in referral_users:
                user.is_refferal = True
            else:
                user.is_refferal = False
            users.append((user.id, user.is_refferal,))
        return [(True, 'Реферал'), (False, 'Не реферал')]

    def queryset(self, request, queryset):
        referral_users = [ru[0] for ru in ReferralUsers.objects.all().values_list('user__id')]
        if self.value() == 'True':
            return queryset.filter(id__in=referral_users)
        if self.value() == 'False':
            return queryset.exclude(id__in=referral_users)

        # if self.value() == True:
        #     return queryset.filter(is_refferal=True)
        # if self.value() == False:

        #     return queryset.filter(is_refferal=False)