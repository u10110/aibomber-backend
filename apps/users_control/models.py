from django.db import models
from apps.authentication.models import User


class ReferalCounter(models.Model):
    class Meta:
        verbose_name = "Реферальный бонус"
        verbose_name_plural = "Реферальные бонусы"

    client = models.ForeignKey(User, on_delete=models.CASCADE, unique=True)
    bonus = models.PositiveIntegerField(default=10)
    privileged = models.BooleanField(default=False)
    sub_bonus = models.PositiveIntegerField(default=3)
    balance = models.PositiveIntegerField()


class UsersAgreement(models.Model):
    class Meta:
        verbose_name = "Соглашение на рассылку"
        verbose_name_plural = "Соглашение на рассылку"

    client = models.ForeignKey(User, on_delete=models.CASCADE, unique=True)
    phone_agree = models.BooleanField(default=True)
    mail_agree = models.BooleanField(default=True)
