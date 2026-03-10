from email.policy import default

from django.db import models

from apps.authentication.models import User
from apps.home.models import ClientSettings


class Promocode(models.Model):
    class Meta:
        verbose_name = "промокоды"
        verbose_name_plural = "Промокоды"

    types = (
        ("general", "general"),
        ("unique", "unique"),
    )
    promocode = models.CharField(max_length=100, null=False)
    type = models.CharField(
        max_length=100, null=False, default="general", choices=types
    )
    used_times = models.IntegerField(default=0)
    client = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
    discount = models.IntegerField(null=False)
    expired_at = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    is_manager = models.BooleanField(default=False)
    for_billing = models.BooleanField(default=True)
    for_prolongation = models.BooleanField(default=False)

    def __str__(self):
        return self.promocode


class TariffCalculated(models.Model):
    client = models.ForeignKey(User, on_delete=models.CASCADE, null=False)
    created_at = models.DateTimeField(auto_now_add=True, null=False)
    buyout_limit = models.IntegerField(null=False)
    review_limit = models.IntegerField(null=False)
    like_limit = models.IntegerField(null=False)
    question_limit = models.IntegerField(null=False)
    like_review_limit = models.IntegerField(null=False)
    search_promotion = models.IntegerField(null=False)
    monitor = models.IntegerField(null=False)
    monitoring_kz = models.IntegerField(null=False)
    adv_company = models.IntegerField(null=False)
    monitoring_rate = models.BooleanField(default=False, null=False)
    course_autobuy = models.BooleanField(default=0, null=False)
    price = models.FloatField(null=False)

    class Meta:
        verbose_name = "тарифы из калькулятора"
        verbose_name_plural = "Тарифы из калькулятора"


class Order(models.Model):
    class Meta:
        verbose_name = "ордера"
        verbose_name_plural = "Ордера"

    client = models.ForeignKey(User, on_delete=models.CASCADE, null=False)
    tariff = models.CharField(max_length=55, null=True)
    period_months = models.IntegerField(null=False)
    paid_status = models.BooleanField(null=False)
    created_at = models.DateTimeField(auto_now_add=True, null=False)
    promocode = models.ForeignKey(Promocode, on_delete=models.CASCADE, null=True)
    is_calculated = models.BooleanField(default=False)
    calculated_tariff = models.ForeignKey(
        TariffCalculated, on_delete=models.CASCADE, null=True, blank=True
    )
    is_prolongation = models.BooleanField(default=False)  # work since 19.08.2022
    prolongation_to = models.IntegerField(null=True, blank=True)
    refered = models.BooleanField(default=False)
    price = models.IntegerField(default=0)


class Paid(models.Model):
    class Meta:
        verbose_name = "оплаты"
        verbose_name_plural = "Оплаты"

    client = models.ForeignKey(User, on_delete=models.CASCADE, null=False)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, null=False)
    start_date = models.DateField(null=False)
    end_date = models.DateField(null=False)


class Limits(models.Model):
    class Meta:
        verbose_name = "лимиты"
        verbose_name_plural = "Лимиты"

    client = models.ForeignKey(User, on_delete=models.CASCADE, null=False)
    paid_info = models.ForeignKey(Paid, on_delete=models.CASCADE, null=False)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, null=True, default=None)
    buyout_limit = models.IntegerField(null=False)
    review_limit = models.IntegerField(null=False)
    like_limit = models.IntegerField(null=False)
    question_limit = models.IntegerField(null=False, default=200)
    like_review_limit = models.IntegerField(null=False)
    start_date = models.DateField(null=False)
    end_date = models.DateField(null=False)


class UnicTariff(models.Model):
    class Meta:
        verbose_name = "уникальные тарифы"
        verbose_name_plural = "Уникальные тарифы"

    title = models.CharField(max_length=200, null=False)
    descriptions = models.TextField(null=True)
    days = models.IntegerField(null=False)
    end_date = models.DateField(null=False)
    buyout_limit = models.IntegerField(null=False)
    review_limit = models.IntegerField(null=False)
    like_limit = models.IntegerField(null=False)
    question_limit = models.IntegerField(null=False)
    like_review_limit = models.IntegerField(null=False)
    positions_limit = models.IntegerField(default=0, null=True)
    course_autobuy = models.BooleanField(default=0, null=False)
    monitoring_rate = models.BooleanField(default=False, null=False)
    monitor = models.IntegerField(null=False, default=0)
    price_dict = models.JSONField(null=True, default=list)

    def __str__(self):
        return self.title


class Bank(models.Model):
    class Meta:
        verbose_name = "Банки"
        verbose_name_plural = "Банки"

    clientsettings = models.ManyToManyField(
        ClientSettings, related_name="Bank"
    )
    name = models.CharField(null=True, max_length=55)
    name_rus = models.CharField(null=True, max_length=55)
    code = models.CharField(null=True, max_length=55)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)
