from apps.authentication.models import User
from apps.home.models import ClientSettings
from django.contrib.auth import get_user_model
from django.db import models

# User = get_user_model()


class Allert(models.Model):
    client_settings = models.ForeignKey(
        ClientSettings, on_delete=models.CASCADE, related_name="Allert", null=True
    )
    title = models.TextField(null=True)
    message = models.TextField(null=True)
    updated_at = models.DateTimeField(
        null=True, auto_now_add=True
    )  # TODO: remove apdated_at tull true


class TgMessage(models.Model):
    class Meta:
        verbose_name = "сообщение"
        verbose_name_plural = "TG сообщения"

    tg_chat_id = models.CharField(max_length=512, null=True)
    first_name = models.CharField(max_length=512, null=True)
    last_name = models.CharField(max_length=512, null=True)
    username = models.CharField(max_length=512, null=True)
    date = models.CharField(max_length=512, null=True)
    text = models.TextField(null=True)
    updated_at = models.DateTimeField(
        null=True, auto_now_add=True
    )  # TODO: remove apdated_at tull true


class ZennoPoster(models.Model):
    sale_id = models.CharField(max_length=512, null=True)
    tg_chat_id = models.CharField(max_length=512, null=True)
    email = models.CharField(max_length=512, null=True)
    date_end = models.DateField(null=True)
    updated_at = models.DateTimeField(
        null=True, auto_now_add=True
    )  # TODO: remove apdated_at tull true


class NotificationMessage(models.Model):
    class Meta:
        verbose_name = "уведомление"
        verbose_name_plural = "Уведомления"

    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    active_until = models.DateField(null=True)


class NotificationRead(models.Model):
    class Meta:
        verbose_name = "прочтенное уведомление"
        verbose_name_plural = "Прочтенные уведомления"

    client = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.ForeignKey(NotificationMessage, on_delete=models.CASCADE)
    read_at = models.DateTimeField(auto_now_add=True)
