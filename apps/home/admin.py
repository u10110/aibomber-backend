from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from django.db.models import Count
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from import_export.admin import ExportActionMixin

from .models import *
from .services.filters import (
    ActionCountFilter,
    DevErrCountFilter,
    StatusCountByDateFilter,
    StatusCountByDatetimeFilter,
    StatusCountWithoutDateFilter,
)
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


class ProductBuyoutAdmin(admin.ModelAdmin):
    actions = [make_done, make_not_payed, make_ready, make_delivery, make_active]
    list_display = (
        "id",
        "get_client_phone",
        "client",
        "product",
        "buyout_date",
        "status",
        "payment_status",
        "pay_type",
        "phone",
        "full_name",
        "code",
        "size",
        "updated_at",
        "pvz",
        "dev_err",
        "pay_method",
        "price_buy",
        "delivery_description",
        "tg_start_date",
        "tg_end_date",
        "created_at"
        # "qr",
    )
    search_fields = (
        "id",
        "client__id",
        "client__phone",
        "phone",
        "status",
        "product__sku",
        "pvz__address",
    )
    # TODO clean and add DevErrCountFilter
    list_filter = (
        StatusCountByDatetimeFilter,
        "payment_status",
        "pay_type",
        "pay_method",
        "buyout_date",
    )  # DevErrCountFilter
    title = "active - в плане на выкуп, delivery - в доставке, ready - готов к получению, done - забран, error - ошибка при попытки выкупа, mp_error - товар был заказн, но пропал из аккаунта"
    fieldsets = (
        (
            title,
            {"fields": ("status", "phone", "full_name", "payment_status", "size")},
        ),
    )

    change_form_template = "admin/browser.html"

    @admin.display(ordering="get_client_phone", description="client phone")
    def get_client_phone(self, obj, description="client phone"):
        return obj.client.phone

    def response_change(self, request, obj):
        if "_get_selenium_url" in request.POST:
            phone = request.POST["phone"]
            print(phone)
            selenium_link = create_ui_instance(phone)
            print(selenium_link)
            return HttpResponseRedirect(selenium_link)
        # return super().response_change(request, obj)
        return HttpResponseRedirect("/dev-admin8/home/productbuyout/")


@admin.action(description="Status - done")
def make_done_review(modeladmin, request, queryset):
    queryset.update(status="done")


@admin.action(description="Status - plan")
def make_plan_review(modeladmin, request, queryset):
    queryset.update(status="plan")


class AddingReviewAdmin(admin.ModelAdmin):
    actions = [make_done_review, make_plan_review]
    list_display = (
        "id",
        "client_id",
        "client",
        "status",
        "get_account",
        "buyout_id",
        "get_product",
        "review_date",
        "star",
        "status_description",
        "text",
        "image1",
        "image2",
        "updated_at",
    )
    search_fields = (
        "id",
        "client__phone",
        "client__id",
        "buyout__product__sku",
        "text",
    )

    list_filter = ("star", "review_date", "status", "status_description")

    fields = ("status", "review_date", "text")

    @admin.display(ordering="get_product", description="Sku")
    def get_product(self, obj, description="Sku"):
        return obj.buyout.product.sku

    @admin.display(ordering="get_account", description="Account")
    def get_account(self, obj, description="Account"):
        return obj.buyout.phone


class ClientSettingsAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "client_id",
        "client",
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
            {"fields": ("tg_chat_id", "tg_token")},
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
        StatusCountByDatetimeFilter,
        "question_date",
    )
    fields = ("status",)

    def client_phone(self, obj):
        return obj.client.phone


class BoostLikeAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "client_id",
        "client",
        "status",
        "url_type",
        "url",
        "updated_at",
    )
    search_fields = ("id", "client__phone", "client__id")
    list_filter = (StatusCountWithoutDateFilter, "url_type")
    fields = ("status",)


class ClientCardAdmin(CustomModelAdmin):
    search_fields = ("client__phone",)


class BoostLikeReviewAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "client_id",
        "client",
        "status",
        "action",
        "product",
        "url",
        "sender_name",
        "id_sender",
        "account_id",
        "account",
        "created_at",
    )
    search_fields = (
        "id",
        "client__phone",
        "url",
        "status",
        "sender_name",
        "product__sku",
        "account__number",
        "client__id",
    )
    list_filter = (
        "action",
        "status",
    )  # TODO add ActionCountFilter - don't working searching by filter
    fields = ("status",)


class ProxyAdmin(CustomModelAdmin):
    pass
    # search_fields = ('client__phone',)


class DBSAdmin(CustomModelAdmin):
    pass


class ClientCardAdmin(CustomModelAdmin):
    pass


class ProductReviewAdmin(CustomModelAdmin):
    pass


class BoostExpectationAdmin(CustomModelAdmin):
    pass


class BoostBasketAdmin(CustomModelAdmin):
    pass


class ClientPvzAdmin(admin.ModelAdmin):
    list_display = (
        "client_id",
        "client",
        "marketplace",
        "get_pvz_address",
        "sms_cloud",
        "count_ordered",
        "updated_at",
    )
    search_fields = ("client__phone", "client__id")
    list_filter = ("marketplace",)

    @admin.display(ordering="get_pvz_address", description="address")
    def get_pvz_address(self, obj):
        return obj.pvz.address


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


admin.site.register(Account, AccountAdmin)
# admin.site.register(ClientProduct, ClientProductAdmin)
# admin.site.register(DBS, DBSAdmin)
admin.site.register(ProductBuyout, ProductBuyoutAdmin)
admin.site.register(AddingReview, AddingReviewAdmin)
admin.site.register(ClientSettings, ClientSettingsAdmin)
# admin.site.register(Pvz, PvzAdmin)
admin.site.register(BoostLike, BoostLikeAdmin)
admin.site.register(BoostQuestion, BoostQuestionAdmin)
admin.site.register(BoostLikeReview, BoostLikeReviewAdmin)
admin.site.register(Proxy, ProxyAdmin)
admin.site.register(ClientPvz, ClientPvzAdmin)
admin.site.register(ReferralLinks, ReferralLinksAdmin)
admin.site.register(ReferralUsers, ReferralUsersAdmin)
admin.site.register(ClientPhrase, ClientPhraseAdmin)
admin.site.register(Phrase, PhraseAdmin)
# admin.site.register(ClientCard, ClientCardAdmin)
# admin.site.register(BoostExpectation, BoostExpectationAdmin)
# admin.site.register(BoostBasket, BoostBasketAdmin)
# admin.site.register(BoostReview, BoostReviewAdmin) # TRASH?
# admin.site.register(ProductReview, ProductReviewAdmin) # TRASH?
