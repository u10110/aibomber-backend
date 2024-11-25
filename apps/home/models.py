from http import client

from django.db import models

from apps.authentication.models import User

# from sqlalchemy import null


class Proxy(models.Model):
    class Meta:
        verbose_name = "прокси"
        verbose_name_plural = "Прокси"

    # pvz_id = models.AutoField(primary_key=True)
    value = models.CharField(max_length=512)
    updated_at = models.DateTimeField(null=True, auto_now_add=True)



class ClientSettings(models.Model):
    class Meta:
        verbose_name = "настройки"
        verbose_name_plural = "Настройки"

    client = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="ClientSettings"
    )
    tg_chat_id = models.TextField(null=True, blank=True)
    tg_token = models.TextField(null=True, blank=True)
    # wb_token = models.TextField(null=True, blank=True)
    updated_at = models.DateTimeField(null=True, auto_now_add=True)
    # tochka_number = models.ForeignKey(
    #     TochkaNumbers, on_delete=models.CASCADE, null=True
    # )
    wb_updated = models.DateTimeField(null=True)



class ReferralLinks(models.Model):
    referrer = models.ForeignKey(User, on_delete=models.CASCADE)
    code = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "реферальная ссылка"
        verbose_name_plural = "Реферальные ссылки"


class ReferralClickCounter(models.Model):
    source = models.ForeignKey(ReferralLinks, on_delete=models.CASCADE)
    ip = models.CharField(max_length=100)


class ReferralUsers(models.Model):
    source = models.ForeignKey(ReferralLinks, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    class Meta:
        verbose_name = "реферальный пользователь"
        verbose_name_plural = "Реферальные пользователи"



class AmoCrm(models.Model):
    website = models.JSONField()
    tg = models.JSONField()


class Project(models.Model):
    class Meta:
        verbose_name = "Проект"
        verbose_name_plural = "Проекты"


    GPT_VERSION_CHOICES = [
        (1, 'OpenAI GPT-4o'),
        (2, 'OpenAI GPT-4o mini'),
    ]
    OPTIONS = [
        (1, 'Входящие'),
        (2, 'Входящие и исходящие'),
    ]

    client = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=1000)
    status = models.CharField(max_length=55, default="active")
    work_option = models.IntegerField(choices=OPTIONS, default=1)
    gpt_version = models.IntegerField(choices=GPT_VERSION_CHOICES, default=1)
    prompt = models.TextField()
    file = models.ImageField(null=True, upload_to="images/")
    updated_at = models.DateTimeField(auto_now=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)


class Chat(models.Model):
    class Meta:
        verbose_name = "Чаты"
        verbose_name_plural = "Чаты"

    client = models.ForeignKey(User, on_delete=models.CASCADE)
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    user_id = models.CharField(max_length=1000)
    status = models.CharField(max_length=55, default="active")
    user_name = models.CharField(max_length=55, default="active")
    user_message = models.CharField(max_length=55, default="active")
    user_anwser = models.CharField(max_length=55, default="active")
    sex = models.IntegerField(null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    # question_date = models.DateTimeField()

