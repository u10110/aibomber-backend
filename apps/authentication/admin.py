from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _
from import_export.admin import ImportExportModelAdmin
from import_export.resources import ModelResource
from import_export.fields import Field

from .services.filters import ReferralFilter
from apps.home.models import ReferralUsers

# from apps.home.models import ProductBuyout


# class CustomUserAdminnline(admin.StackedInline):
# model = ProductBuyout

class CustomUserResource(ModelResource):
    is_referral = Field(column_name="is_referral")

    def dehydrate_is_referral(self, obj):
        if ReferralUsers.objects.filter(user=obj.id):
            return True
        return False
    class Meta:
        model = get_user_model()
        fields = ("id",
                "phone",
                "is_active",
                "date_joined",
                "email",
                "first_name",
                "last_name",
                "is_staff",
                "last_login",
                "is_referral")


class CustomUserAdmin(ImportExportModelAdmin):  # admin.ModelAdmin
    """Define admin model for custom User model with no username field."""

    fieldsets = (
        (None, {"fields": ("phone", "password")}),
        (_("Personal info"), {"fields": ("first_name", "last_name")}),
        (
            _("Permissions"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                    "is_referral",
                )
            },
        ),
        (_("Important dates"), {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("phone", "password1", "password2"),
            },
        ),
    )
    list_display = (
        "id",
        "phone",
        "is_active",
        "date_joined",
        "email",
        "first_name",
        "last_name",
        "is_staff",
        "last_login",
        "is_referral"
    )
    readonly_fields = ('is_referral',)
    search_fields = ("id", "phone", "first_name", "last_name")
    ordering = ("-id",)
    resource_class = CustomUserResource
    #inlines = [CustomUserAdminnline]

    def is_referral(self, obj):
        if ReferralUsers.objects.filter(user=obj.id):
            return True
        return False
    #
    is_referral.boolean = True

    list_filter = (ReferralFilter, "is_active", "is_staff", "is_superuser", "groups",)


admin.site.register(get_user_model(), CustomUserAdmin)
