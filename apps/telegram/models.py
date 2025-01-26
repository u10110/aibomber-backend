from django.db import models
from apps.home.models import ClientSettings


class PeriodicAlerts(models.Model):
    class Meta:
        verbose_name = "Уведомление"
        verbose_name_plural = "Уведомления"

    clientsettings = models.ForeignKey(
        ClientSettings, on_delete=models.SET_DEFAULT, related_name="PeriodicAlerts", default=None
    )
    period_day = models.SmallIntegerField()
    send_date = models.DateTimeField(null=True)
