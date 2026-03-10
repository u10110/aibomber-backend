import datetime

from apps.billing.models import Promocode
from django.contrib import admin


class PromocodeCountFilter(admin.SimpleListFilter):
    title = "Promocode"
    parameter_name = "promocode_id"

    def lookups(self, request, model_admin):
        qs = model_admin.get_queryset(request)
        print(qs)
        for promocode in (
            qs.values_list(self.parameter_name, flat=True).distinct().order_by()
        ):
            print(promocode)
            count = qs.filter(promocode_id=promocode).count()
            print(promocode, count)
            if promocode is not None:
                promocode = Promocode.objects.get(pk=promocode).promocode
            yield (promocode, f"{promocode} ({count})")

    def queryset(self, request, queryset):
        # Apply the filter selected, if any
        promocode = self.value()
        if promocode:
            return queryset.filter(promocode=promocode)
