from django.db import models
from apps.home.models import ClientSettings


class PeriodicAlerts(models.Model):
    class Meta:
        verbose_name = "Уведомление"
        verbose_name_plural = "Уведомления"

    clientsettings = models.ForeignKey(
        ClientSettings, on_delete=models.CASCADE, related_name="PeriodicAlerts"
    )
    period_day = models.SmallIntegerField()
    send_date = models.DateTimeField(null=True)
