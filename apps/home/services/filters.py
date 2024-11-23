import datetime

from django.contrib import admin


class StatusCountByDatetimeFilter(admin.SimpleListFilter):
    title = "Status"
    parameter_name = "status"

    # parameter_date = self.

    def lookups(self, request, model_admin):
        print(type(model_admin))
        if str(model_admin) == "home.BoostQuestionAdmin":
            variable_column = "question_date"
        elif str(model_admin) == "home.ProductBuyoutAdmin":
            variable_column = "buyout_date"

        search_type = "range"
        filter_r = variable_column + "__" + search_type

        today_min = datetime.datetime.combine(datetime.date.today(), datetime.time.min)
        today_max = datetime.datetime.combine(datetime.date.today(), datetime.time.max)
        qs = model_admin.get_queryset(request)
        print(qs)
        for status in (
            qs.values_list(self.parameter_name, flat=True).distinct().order_by()
        ):
            count = qs.filter(status=status).count()
            count_today = qs.filter(
                **{filter_r: (today_min, today_max)}, status=status
            ).count()
            if count:
                yield (status, f"{status} [{count_today}] ({count})")

    def queryset(self, request, queryset):
        # Apply the filter selected, if any
        status = self.value()
        if status:
            return queryset.filter(status=status)


class StatusCountByDateFilter(admin.SimpleListFilter):
    title = "Status"
    parameter_name = "status"

    # parameter_date = self.

    def lookups(self, request, model_admin):

        search_type = "range"
        filter_r = variable_column + "__" + search_type

        today_min = datetime.datetime.combine(datetime.date.today(), datetime.time.min)
        today_max = datetime.datetime.combine(datetime.date.today(), datetime.time.max)
        qs = model_admin.get_queryset(request)
        for status in (
            qs.values_list(self.parameter_name, flat=True).distinct().order_by()
        ):
            count = qs.filter(status=status).count()
            if count:
                yield (status, f"{status} [{count_today}] ({count})")

    def queryset(self, request, queryset):
        # Apply the filter selected, if any
        status = self.value()
        if status:
            return queryset.filter(status=status)


class StatusCountWithoutDateFilter(admin.SimpleListFilter):
    title = "Status"
    parameter_name = "status"

    def lookups(self, request, model_admin):
        qs = model_admin.get_queryset(request)
        for status in (
            qs.values_list(self.parameter_name, flat=True).distinct().order_by()
        ):
            count = qs.filter(status=status).count()
            if count:
                yield (status, f"{status} ({count})")

    def queryset(self, request, queryset):
        # Apply the filter selected, if any
        status = self.value()
        if status:
            return queryset.filter(status=status)


class ActionCountFilter(admin.SimpleListFilter):
    title = "Action"
    parameter_name = "action"

    def lookups(self, request, model_admin):
        qs = model_admin.get_queryset(request)
        for status in (
            qs.values_list(self.parameter_name, flat=True).distinct().order_by()
        ):
            count = qs.filter(action=status).count()
            if count:
                yield (status, f"{status} ({count})")

    def queryset(self, request, queryset):
        # Apply the filter selected, if any
        status = self.value()
        if status:
            return queryset.filter(status=status)


class DevErrCountFilter(admin.SimpleListFilter):
    title = "Dev Errors"
    parameter_name = "dev_err"

    def lookups(self, request, model_admin):
        qs = model_admin.get_queryset(request)
        for status in (
            qs.values_list(self.parameter_name, flat=True).distinct().order_by()
        ):
            count = qs.filter(dev_err=status).count()
            if count:
                yield (status, f"{status} ({count})")

    def queryset(self, request, queryset):
        # Apply the filter selected, if any
        lang = self.value()
        if lang:
            return queryset.filter(lang=lang)
