# -*- encoding: utf-8 -*-
from django.contrib import admin
from django.http import HttpResponseRedirect
from .models import NotificationMessage, NotificationRead, TgMessage
from .services.telegram import send_message_all_tg_users


# DONE
class TgMessageAdmin(admin.ModelAdmin):
    list_display = (
        "tg_chat_id",
        "first_name",
        "last_name",
        "username",
        "date",
        "text",
        "updated_at",
    )
    search_fields = ("tg_chat_id", "username", "text")


class AllertAdmin(admin.ModelAdmin):
    list_display = ("id", "client_settings", "title", "message", "updated_at")


class NotificationMessageAdmin(admin.ModelAdmin):
    list_display = ("id", "message", "created_at", "is_active", "active_until")

    change_form_template = "alerts/tg-notifications.html"

    def response_add(self, request, obj, post_url_continue=None):
        if "_send-tg-notifications" in request.POST:
            is_delivered = send_message_all_tg_users(request.POST["message"])
            if is_delivered:
                self.message_user(request, "Message was delivered to all tg-users")
            else:
                self.message_user(request, "Message was not delivered. Something bad")
            return HttpResponseRedirect("/dev-admin8/alert/notificationmessage/")
        return super().response_change(request, obj)

    def response_change(self, request, obj):
        if "_send-tg-notifications" in request.POST:
            is_delivered = send_message_all_tg_users(request.POST["message"])
            if is_delivered:
                self.message_user(request, "Message was delivered to all tg-users")
            else:
                self.message_user(request, "Message was not delivered. Something bad")
            return HttpResponseRedirect("/dev-admin8/alert/notificationmessage/")
        return super().response_change(request, obj)


class NotificationReadAdmin(admin.ModelAdmin):
    list_display = ("id", "read_at", "client_id", "message_id")


admin.site.register(TgMessage, TgMessageAdmin)
# admin.site.register(NotificationMessage, NotificationMessageAdmin)
# admin.site.register(NotificationRead, NotificationReadAdmin)
