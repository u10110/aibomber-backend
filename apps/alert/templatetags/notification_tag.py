import datetime
from atexit import register

from apps.alert.models import NotificationMessage, NotificationRead
from django import template
from django.contrib.auth import get_user_model
from django.db.models import Q

User = get_user_model()

register = template.Library()


@register.simple_tag
def get_notifaications(user):
    try:
        user = User.objects.get(id=user.id)
        date_now = datetime.datetime.now(datetime.timezone.utc)
        notifications_readed = NotificationRead.objects.filter(client=user).values_list(
            "message", flat=True
        )
        print(f"rederd {notifications_readed}")
        notifications = (
            NotificationMessage.objects.filter(is_active=True)
            .filter(Q(active_until__gte=date_now) | Q(active_until=None))
            .order_by("-created_at")
        )
        result = []
        for notification in notifications:
            if notification.id not in notifications_readed:
                notification.is_read = False
            else:
                notification.is_read = True
            result.append(notification)
        return result
    except Exception as e:
        print(e)
        return False


@register.simple_tag
def has_new_notifications(user):
    try:
        user = User.objects.get(id=user.id)
        date_now = datetime.datetime.now(datetime.timezone.utc)
        notifications_readed = NotificationRead.objects.filter(client=user).values_list(
            "message", flat=True
        )
        notifications = NotificationMessage.objects.filter(is_active=True).filter(
            Q(active_until__gte=date_now) | Q(active_until=None)
        )
        print(notifications)
        for notification in notifications:
            if notification.id not in notifications_readed:
                notification.is_read = False
                return True
            else:
                notification.is_read = True
        return False
    except Exception as e:
        print(e)
        return False
