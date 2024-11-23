from django.contrib import admin
from django.urls import reverse
from django.utils.safestring import mark_safe
from import_export.admin import ImportExportModelAdmin
from import_export.resources import ModelResource
from import_export.fields import Field

# Register your models here.
from .models import Limits, Order, Paid, Promocode, UnicTariff, TariffCalculated
from .services.filters import PromocodeCountFilter

title = "Promocode -> Order -> Paid -> Limits"


class CustomModelAdmin(admin.ModelAdmin):
    def __init__(self, model, admin_site):
        self.list_display = [
            field.name for field in model._meta.fields if field.name != "id"
        ]
        print(self.list_display)
        super(CustomModelAdmin, self).__init__(model, admin_site)


class TariffCalculatedAdmin(admin.ModelAdmin):
    fieldsets = (
        (
            title,
            {
                "fields": (
                    "client",
                    "price",
                    "buyout_limit",
                    "review_limit",
                    "like_limit",
                    "like_review_limit",
                    "question_limit",
                    "search_promotion",
                    "monitor",
                    "monitoring_kz",
                    "adv_company",
                    "monitoring_rate",
                    "course_autobuy",
                )
            },
        ),
    )
    list_display = (
        "id",
        "client",
        "price",
        "buyout_limit",
        "review_limit",
        "like_limit",
        "like_review_limit",
        "question_limit",
        "search_promotion",
        "monitor",
        "monitoring_kz",
        "adv_company",
        "monitoring_rate",
        "course_autobuy",
        "created_at",
    )
    search_fields = (
        "id",
    )

    @admin.display(ordering="get_client_phone", description="client")
    def get_client_phone(self, obj, description="client"):
        return obj.client.phone


class LimitsAdmin(admin.ModelAdmin):
    fieldsets = (
        (
            title,
            {
                "fields": (
                    "client",
                    "paid_info",
                    "buyout_limit",
                    "review_limit",
                    "like_limit",
                    "like_review_limit",
                    "question_limit",
                    "start_date",
                    "end_date",
                )
            },
        ),
    )
    list_display = (
        "id",
        "client_id",
        "get_client_phone",
        "paid_for",
        "buyout_limit",
        "review_limit",
        "like_limit",
        "like_review_limit",
        "question_limit",
        "start_date",
        "end_date",
    )
    search_fields = (
        "id",
        "client__id",
        "paid_info__id",
    )

    @admin.display(ordering="get_client_phone", description="client")
    def get_client_phone(self, obj, description="client"):
        return obj.client.phone

    def paid_for(self, obj):
        link = "%s?q=%s" % (
        reverse('admin:billing_paid_changelist'), obj.paid_info.id)  # model name has to be lowercase
        return mark_safe(u'<a href="%s">%s</a>' % (link, obj.paid_info.id))


class LimitsInline(admin.TabularInline):  # StackedInline
    autocomplete_fields = ['order']
    model = Limits


class PaidInline(admin.TabularInline):  # StackedInline
    model = Paid
    inlines = [
        LimitsInline,
    ]


class OrderResource(ModelResource):
    prolongation_to_for = Field(column_name='prolongation_to_for')
    price = Field(column_name='price')
    promocode = Field(column_name='promocode')
    calculated_tariff_for = Field(column_name='calculated_tariff_for')

    class Meta:
        model = Order
        fields = ("id",
                  "client__phone",
                  "client__id",
                  "tariff",
                  "period_months",
                  "paid_status",
                  "promocode",
                  "is_calculated",
                  "calculated_tariff_for",
                  "is_prolongation",
                  "prolongation_to_for",
                  "created_at",)

        export_order = ['id', 'client__id', 'client__phone', 'tariff','period_months',
                        'paid_status', 'price', 'promocode', "is_calculated", "calculated_tariff_for",
                        "is_prolongation", 'prolongation_to_for', 'created_at']

    def dehydrate_calculated_tariff_for(self, obj):
        if obj.calculated_tariff:
            return obj.calculated_tariff.id

    def dehydrate_prolongation_to_for(self, obj):
        if obj.prolongation_to:
            return obj.prolongation_to

    def dehydrate_promocode(self, obj):
        if obj.promocode:
            return obj.promocode.promocode

    def dehydrate_price(self, obj):
        count_months = obj.period_months
        is_prolongation = False
        if count_months == 1:
            prices = [4900, 8900, 19900, 49900]
        elif count_months == 3:
            prices = [13230, 24030, 53730, 134730]
        elif count_months == 6:
            prices = [23520, 42720, 95520, 239520]
        elif count_months == 12:
            prices = [41160, 74760, 167160, 419160]
        else:
            is_prolongation = True
            prices = [4900, 8900, 19900, 49900]

        if obj.is_calculated == True:
            price = obj.calculated_tariff.price
        elif obj.tariff == "showroom":
            price = prices[0]
        elif obj.tariff == "market":
            price = prices[1]
        elif obj.tariff == "hypermarket":
            price = prices[2]
        elif obj.tariff == "magigrand":
            price = prices[3]
        else:
            price = 0

        if is_prolongation:
            price = price * count_months

        if obj.promocode:
            price = int(price * (100 - obj.promocode.discount) / 100)
        return price


class OrderAdmin(ImportExportModelAdmin):
    fieldsets = (
        (
            title,
            {
                "fields": (
                    "client",
                    "tariff",
                    "period_months",
                    "is_calculated",
                    "calculated_tariff",
                    "is_prolongation",
                    "prolongation_to",
                    "paid_status",
                )
            },
        ),
    )
    inlines = [PaidInline]

    # fields = ('client_phone',)
    list_display = (
        "id",
        # "clientphone",
        "client",
        "client_phone",
        "tariff",
        "period_months",
        "paid_status",
        "price",
        "promocode",
        "is_calculated",
        "calculated_tariff_for",
        "is_prolongation",
        "prolongation_to_for",
        "created_at",
    )
    search_fields = (
        "id",
        "client__id",
        "prolongation_to",
    )
    list_filter = (
        # PromocodeCountFilter,
        "promocode__promocode",
        "paid_status",
        "tariff",
        "period_months",
        "is_calculated",
        "is_prolongation",
        "created_at",
    )
    resource_class = OrderResource

    # @admin.display(ordering="get_client", description="client")
    # def get_client(self, obj, description="client"):
    #     return obj.client.id

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset

    # @admin.display(ordering="get_client_phone", description="client phone")
    def client_phone(self, obj):
        return obj.client.phone

    def calculated_tariff_for(self, obj):
        if obj.calculated_tariff != None:
            link = "%s?q=%s" % (reverse('admin:billing_tariffcalculated_changelist'),
                                obj.calculated_tariff.id)  # model name has to be lowercase
            return mark_safe(u'<a href="%s">%s</a>' % (link, obj.calculated_tariff.id))
        else:
            return None

    def prolongation_to_for(self, obj):
        if obj.prolongation_to != None:
            link = "%s?q=%s" % (
            reverse('admin:billing_order_changelist'), obj.prolongation_to)  # model name has to be lowercase
            return mark_safe(u'<a href="%s">%s</a>' % (link, obj.prolongation_to))
        else:
            return None

    def price(self, obj):
        count_months = obj.period_months
        is_prolongation = False
        if count_months == 1:
            prices = [4900, 8900, 19900, 49900]
        elif count_months == 3:
            prices = [13230, 24030, 53730, 134730]
        elif count_months == 6:
            prices = [23520, 42720, 95520, 239520]
        elif count_months == 12:
            prices = [41160, 74760, 167160, 419160]
        else:
            is_prolongation = True
            prices = [4900, 8900, 19900, 49900]

        if obj.is_calculated == True:
            price = obj.calculated_tariff.price
        elif obj.tariff == "showroom":
            price = prices[0]
        elif obj.tariff == "market":
            price = prices[1]
        elif obj.tariff == "hypermarket":
            price = prices[2]
        elif obj.tariff == "magigrand":
            price = prices[3]
        else:
            price = 0

        if is_prolongation:
            price = price * count_months

        if obj.promocode:
            price = int(price * (100 - obj.promocode.discount) / 100)
        return price


class PaidResource(ModelResource):
    price = Field(column_name="price")

    def dehydrate_price(self, obj):
        count_months = obj.order.period_months
        is_prolongation = False
        if count_months == 1:
            prices = [4900, 8900, 19900, 49900]
        elif count_months == 3:
            prices = [13230, 24030, 53730, 134730]
        elif count_months == 6:
            prices = [23520, 42720, 95520, 239520]
        elif count_months == 12:
            prices = [41160, 74760, 167160, 419160]
        else:
            is_prolongation = True
            prices = [4900, 8900, 19900, 49900]

        if obj.order.is_calculated == True:
            price = obj.order.calculated_tariff.price
        elif obj.order.tariff == "showroom":
            price = prices[0]
        elif obj.order.tariff == "market":
            price = prices[1]
        elif obj.order.tariff == "hypermarket":
            price = prices[2]
        elif obj.order.tariff == "magigrand":
            price = prices[3]
        else:
            price = 0

        if is_prolongation:
            price = price * count_months

        if obj.order.promocode:
            price = int(price * (100 - obj.order.promocode.discount) / 100)
        return price

    class Meta:
        model = Paid
        fields = ("id",
                  "client__id",
                  "client__phone",
                  "order_id",
                  "start_date",
                  "end_date",
                  "order__created_at",
                  "price")


class PaidAdmin(ImportExportModelAdmin):
    fieldsets = (
        (
            title,
            {
                "fields": (
                    "start_date",
                    "end_date",
                    "order"
                )
            },
        ),
    )
    inlines = [
        LimitsInline,
    ]
    list_display = (
        "id",
        "client_id",
        "get_client_phone",
        'price',
        "order_for",
        "start_date",
        "end_date"
    )
    search_fields = (
        "id",
        "client__id",
        "order__id",
    )
    resource_class = PaidResource

    @admin.display(ordering="get_client_phone", description="client")
    def get_client_phone(self, obj, description="client"):
        return obj.client.phone

    def order_for(self, obj):
        link = "%s?q=%s" % (reverse('admin:billing_order_changelist'), obj.order.id)  # model name has to be lowercase
        return mark_safe(u'<a href="%s">%s</a>' % (link, obj.order.id))

    def price(self, obj):
        count_months = obj.order.period_months
        is_prolongation = False
        if count_months == 1:
            prices = [4900, 8900, 19900, 49900]
        elif count_months == 3:
            prices = [13230, 24030, 53730, 134730]
        elif count_months == 6:
            prices = [23520, 42720, 95520, 239520]
        elif count_months == 12:
            prices = [41160, 74760, 167160, 419160]
        else:
            is_prolongation = True
            prices = [4900, 8900, 19900, 49900]

        if obj.order.is_calculated == True:
            price = obj.order.calculated_tariff.price
        elif obj.order.tariff == "showroom":
            price = prices[0]
        elif obj.order.tariff == "market":
            price = prices[1]
        elif obj.order.tariff == "hypermarket":
            price = prices[2]
        elif obj.order.tariff == "magigrand":
            price = prices[3]
        else:
            price = 0

        if is_prolongation:
            price = price * count_months

        if obj.order.promocode:
            price = int(price * (100 - obj.order.promocode.discount) / 100)
        return price


class UnicTariffAdmin(admin.ModelAdmin):
    fieldsets = (
        (
            "https://t.me/mplabio_bot?start={Title}",
            {
                "fields": (
                    "title",
                    "descriptions",
                    "days",
                    "end_date",
                    "buyout_limit",
                    "review_limit",
                    "like_limit",
                    "question_limit",
                    "like_review_limit",
                    "positions_limit",
                    "course_autobuy",
                    "monitoring_rate",
                    "price_dict"
                )
            },
        ),
    )
    list_display = (
        "id",
        "title",
        "descriptions",
        "days",
        "end_date",
        "buyout_limit",
        "review_limit",
        "like_limit",
        "question_limit",
        "like_review_limit",
        "positions_limit",
        "course_autobuy",
        "monitoring_rate",
    )
    search_fields = (
        "id",
        "title",
        "descriptions",
    )


class PromocodeAdmin(admin.ModelAdmin):
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "type",
                    "promocode",
                    # "client_id",
                    "expired_at",
                    "discount",
                    "is_manager",
                    "for_billing",
                    "for_prolongation"
                )
            },
        ),
    )
    list_display = (
        "id",
        "type",
        "promocode",
        "discount",
        "client",
        "used_times",
        "is_manager",
        "for_billing",
        "for_prolongation",
        "expired_at",
        "created_at",
    )
    search_fields = ("promocode",)
    list_filter = ("type", "expired_at", "created_at")


admin.site.register(Promocode, PromocodeAdmin)
admin.site.register(Order, OrderAdmin)
admin.site.register(Paid, PaidAdmin)
admin.site.register(Limits, LimitsAdmin)
admin.site.register(UnicTariff, UnicTariffAdmin)
admin.site.register(TariffCalculated, TariffCalculatedAdmin)
# admin.site.register(Paid, PaidWithSumAdmin)
