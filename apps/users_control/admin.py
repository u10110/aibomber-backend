from django.contrib import admin
from .models import ReferalCounter, UsersAgreement
from django.http import HttpResponse, HttpResponseRedirect
from apps.billing.models import Order
from apps.home.models import ReferralUsers, ReferralLinks
from import_export.admin import ImportExportModelAdmin
from import_export.resources import ModelResource


class ReferalCounterResource(ModelResource):
    class Meta:
        model = ReferalCounter
        fields = ("id",
                  "client",
                  "client__phone",
                  "bonus",
                  "balance",
                  "privileged",
                  "sub_bonus",)

        export_order = ["id",
                        "client",
                        "client__phone",
                        "bonus",
                        "balance",
                        "privileged",
                        "sub_bonus", ]


@admin.register(ReferalCounter)
class ReferalAdmin(ImportExportModelAdmin):
    list_display = [
        "id",
        "client",
        "client_phone",
        "bonus",
        "balance",
        "privileged",
        "sub_bonus"
    ]
    search_fields = ["id", "client__id", "client__phone"]

    change_form_template = "admin/referal.html"
    resource_class = ReferalCounterResource

    def response_change(self, request, obj):
        if "_get_balance" in request.POST:
            print(request.POST)
            referral_object = ReferralLinks.objects.get(referrer=obj.client)
            users_signup = ReferralUsers.objects.filter(source=referral_object)
            for user in users_signup:
                Order.objects.filter(client=user.user, paid_status=True, refered=False).update(refered=True)
            obj.balance = 0
            obj.save()
            return HttpResponseRedirect("/dev-admin8/users_control/referalcounter")

        return HttpResponseRedirect("/dev-admin8/users_control/referalcounter")

    def client_phone(self, obj):
        return obj.client.phone


@admin.register(UsersAgreement)
class AgreeAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "client",
        "phone_agree",
        "mail_agree",
    ]
    search_fields = ("id", "client",)
