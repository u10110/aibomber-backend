from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from django.db.models import Count
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from .models import *

from .services.UI import create_ui_instance

admin.site.site_header = "Администрирование MPLAB"
admin.site.index_title = "Функциональная Область"
admin.site.site_title = "k.loginov.dev@gmail.com"


class CustomModelAdmin(admin.ModelAdmin):
    def __init__(self, model, admin_site):
        self.list_display = [field.name for field in model._meta.fields]
        print(self.list_display)
        super(CustomModelAdmin, self).__init__(model, admin_site)


class AccountAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "number",
        "full_name",
        "sex",
    )
    search_fields = ("number", "full_name", "id")
    list_filter = ("status", "sex")

    change_form_template = "admin/browser.html"

    def response_change(self, request, obj):
        if "_get_selenium_url" in request.POST:
            phone = request.POST["number"]
            print(phone)
            selenium_link = create_ui_instance(phone)
            print(selenium_link)
            return HttpResponseRedirect(selenium_link)
        # return super().response_change(request, obj)
        return HttpResponseRedirect("/dev-admin8/home/account/")


class ClientProductAdmin(admin.ModelAdmin):
    list_display = ("client_id", "client", "sku", "title", "price")
    search_fields = ("client__phone",)

class PhoneAdmin(admin.ModelAdmin):
    list_display = ('phone', 'updated_at', 'created_at')  # Поля, которые отображаются в списке
    list_filter = ('updated_at', 'created_at')  # Возможность фильтрации
    search_fields = ('phone',)  # Поле для поиска
    ordering = ('-created_at',)  # Сортировка по умолчанию

@admin.action(description="Payment Status - done")
def make_done(modeladmin, request, queryset):
    queryset.update(payment_status="done")


@admin.action(description="Payment Status - not_payed")
def make_not_payed(modeladmin, request, queryset):
    queryset.update(payment_status="not_payed")


@admin.action(description="Status - ready")
def make_ready(modeladmin, request, queryset):
    queryset.update(status="ready")


@admin.action(description="Status - delivery")
def make_delivery(modeladmin, request, queryset):
    queryset.update(status="delivery")


@admin.action(description="Status - active")
def make_active(modeladmin, request, queryset):
    queryset.update(status="active")



@admin.action(description="Status - done")
def make_done_review(modeladmin, request, queryset):
    queryset.update(status="done")


@admin.action(description="Status - plan")
def make_plan_review(modeladmin, request, queryset):
    queryset.update(status="plan")


class ClientSettingsAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "client_id",
        "client",
        "balance",
        "tg_chat_id",
        "tg_token",
        "updated_at",
    )
    search_fields = ("id", "client__phone", "client__id")
    # fileds = ("mode", "sms_cloud", "sms_cloud_in_process", "tg_chat_id", "tg_token")
    title = "Modes: 1 - clound, 2 - tg"
    fieldsets = (
        (
            title,
            {"fields": ("tg_chat_id", "tg_token", "balance")},
        ),
    )


class PvzAdmin(admin.ModelAdmin):
    list_display = ("marketplace", "lat", "lon", "address", "status", "updated_at")
    search_fields = ("address",)
    list_filter = ("marketplace", "status")


@admin.action(description="Status - active")
def make_active_questions(modeladmin, request, queryset):
    queryset.update(status="active")


class BoostQuestionAdmin(admin.ModelAdmin):
    actions = [make_active_questions]
    list_display = (
        "id",
        "client_id",
        "client_phone",
        "status",
        "question_date",
        "sku",
        "question_text",
        "account_id",
    )
    search_fields = (
        "id",
        "client__phone",
        "sku",
        "status",
        "question_text",
        "client__id",
    )
    list_filter = (
        "question_date",
    )
    fields = ("status",)

    def client_phone(self, obj):
        return obj.client.phone




class ClientCardAdmin(CustomModelAdmin):
    search_fields = ("client__phone",)



class ProxyAdmin(CustomModelAdmin):
    pass
    # search_fields = ('client__phone',)



class BoostExpectationAdmin(CustomModelAdmin):
    pass






class ReferralLinksAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "referrer_client",
        "code",
        "is_active",
    )
    search_fields = (
        "id",
        "referrer__phone",
        "referrer__id",
        "code",
    )
    list_filter = ("is_active",)

    def referrer_client(self, obj):
        link = "%s?q=%s" % (
            reverse("admin:authentication_user_changelist"),
            obj.referrer.phone,
        )  # model name has to be lowercase
        return mark_safe('<a href="%s">%s</a>' % (link, obj.referrer.phone))


class ReferralUsersAdmin(admin.ModelAdmin):
    list_display = ("id", "source_id", "source_link", "user_invited", "user_id")
    search_fields = (
        "user__phone",
        "source__id",
        "source__referrer__phone",
    )

    def user_invited(self, obj):
        link = "%s?q=%s" % (
            reverse("admin:authentication_user_changelist"),
            obj.user.phone,
        )  # model name has to be lowercase
        return mark_safe('<a href="%s">%s</a>' % (link, obj.user.phone))

    def source_link(self, obj):
        link = "%s?id=%s" % (
            reverse("admin:home_referrallinks_changelist"),
            obj.source.id,
        )  # model name has to be lowercase
        return mark_safe('<a href="%s">%s</a>' % (link, obj.source.referrer.phone))


class PhraseAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "value",
        "es_id",
        "frequency",
        "updated_at",
        "created_at",
    )
    search_fields = ("id",)
    list_filter = ("updated_at",)


class ClientPhraseAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "client",
        "client_phone",
        "product",
        # "phrase",
        "is_search_promotion",
        "status",
        "status_dev",
        "updated_at",
        "created_at",
        "stoped_at",
    )
    search_fields = ("id",)
    list_filter = ("is_search_promotion",)

    def client_phone(self, obj):
        return obj.client.phone





class ChatAdmin(admin.ModelAdmin):
    pass
    # list_display = (
    #     "id",
    #     "value",
    #     "es_id",
    #     "frequency",
    #     "updated_at",
    #     "created_at",
    # # )
    # search_fields = ("id",)
    # list_filter = ("updated_at",)


class ProjectAdmin(admin.ModelAdmin):
    pass
    # list_display = (
    #     "id",
    #     "value",
    #     "es_id",
    #     "frequency",
    #     "updated_at",
    #     "created_at",
    # )
    # search_fields = ("id",)
    # list_filter = ("updated_at",)

class ChannelAdmin(admin.ModelAdmin):
    pass
    # list_display = (
    #     "id",
    #     "value",
    #     "es_id",
    #     "frequency",
    #     "updated_at",
    #     "created_at",
    # )
    # search_fields = ("id",)
    # list_filter = ("updated_at",)




admin.site.register(Chat, ChatAdmin)
admin.site.register(Project, ProjectAdmin)
admin.site.register(Channel, ChannelAdmin)
admin.site.register(ClientSettings, ClientSettingsAdmin)
admin.site.register(Proxy, ProxyAdmin)
admin.site.register(Phone, PhoneAdmin)
# admin.site.register(ReferralLinks, ReferralLinksAdmin)
# admin.site.register(ReferralUsers, ReferralUsersAdmin)
