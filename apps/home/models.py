from http import client

from django.db import models
from django.db.models.signals import post_save, post_init
from apps.authentication.models import User
import datetime
import requests
import json

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
    balance = models.IntegerField(max_length=55, default=0)
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


class Phone(models.Model):
    phone = models.CharField(max_length=100)
    updated_at = models.DateTimeField(auto_now=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)


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
    AGENT_TYPES = [
        ('sales_manager', 'Менеджер по продажам'),
        ('consultant', 'Консультант'),
        ('support_manager', 'Менеджер поддержки'),
        ('review_manager', 'Менеджер по работе с отзывами'),
        ('info_business_manager', 'Менеджер для инфобиза'),
        ('services_manager', 'Менеджер в сфере услуг'),
        ('health_fitness_manager', 'Менеджер в сфере здоровья и фитнеса'),
    ]

    CRM_TYPES = [
        ('null', 'не выбрано'),
        ('amo_crm', 'Amo Crm'),
        ('bitrix', 'Bitrix 24')
    ]

    STATUS_CHOICES = [
        ('active', 'В работе'),
        ('completed', 'Завершен'),
        ('paused', 'Пауза')
    ]

    client = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=1000)
    agent_type = models.CharField(
        max_length=50,
        choices=AGENT_TYPES,
        default='sales_manager',
        verbose_name="Тип ИИ-агента"
    )
    status = models.CharField(
        max_length=55,
        choices=STATUS_CHOICES,
        default='active',
        verbose_name="Статус"
    )
    is_active = models.BooleanField(default=False)
    work_option = models.IntegerField(choices=OPTIONS, default=1)
    gpt_version = models.IntegerField(choices=GPT_VERSION_CHOICES, default=1)
    hello_text = models.TextField(null=True)
    prompt = models.TextField()
    knowledge_base_text = models.TextField(null=True, blank=True)
    google_doc = models.URLField(
        null=True,
        blank=True,
        help_text="Ссылка на Google-документ (необязательно)"
    )
    per_conversation_limit = models.IntegerField(
        default=50,
        verbose_name="Лимит на одну переписку"
    )

    outgoing_limit = models.IntegerField(
        default=30,  # Значение по умолчанию
        verbose_name="Ограничение исходящих"
    )
    message_limit = models.IntegerField(default=30)

    integrations = models.CharField(
        max_length=50,
        choices=CRM_TYPES,
        default='null',
        verbose_name="Интеграция"
    )

    time_start = models.TimeField(default=datetime.time(8, 0))
    time_end = models.TimeField(default=datetime.time(22, 0))
    updated_at = models.DateTimeField(auto_now=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)

    def get_status_display(self):
        return dict(self.STATUS_CHOICES).get(self.status, self.status)

    def get_agent_type_display(self):
        return dict(self.AGENT_TYPES).get(self.agent_type, self.agent_type)


class ProjectFile(models.Model):
    project = models.ForeignKey(Project, related_name="files", on_delete=models.CASCADE)
    file = models.FileField(
        upload_to="uploads/files/",
        help_text="Допустимые форматы: PDF, TXT, DOC, DOCX, XLSX, CSV, XSLM"
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)


class Recipient(models.Model):
    class Meta:
        verbose_name = "Получатели"
        verbose_name_plural = "Получатели"

    OPTIONS = [
        (1, 'Белый список'),
        (2, 'Черный список'),
    ]

    client = models.ForeignKey(User, on_delete=models.CASCADE)
    project_id = models.IntegerField(null=True)
    title = models.CharField(max_length=1000)
    status = models.CharField(max_length=55, default="active")
    work_option = models.IntegerField(choices=OPTIONS, default=1)
    remote_ids = models.TextField(default='')
    updated_at = models.DateTimeField(auto_now=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)

    def __str__(self):
        return self.title


class Channel(models.Model):
    class Meta:
        verbose_name = "Канал"
        verbose_name_plural = "Каналы"
    STATUS_CHOICES = [
            ('unauthorized', 'Не авторизован'),
            ('authorized', 'Авторизован'),
            ('banned', 'Заблокирован'),
        ]
    SOURCE_CHOICES = [
        ('telegram', 'Telegram'),
        ('avito', 'Avito'),
        ('web_widget', 'Web Widget'),
        ('vk', 'VK'),
        ('email', 'E-mail'),
        ('whatsapp', 'WhatsApp'),
        ('instagram', 'Instagram'),
    ]

    client = models.ForeignKey(User, on_delete=models.CASCADE)
    project_id = models.IntegerField(null=True)
    title = models.CharField(max_length=1000)
    is_active = models.BooleanField(default=False)
    source = models.CharField(
        max_length=20,
        choices=SOURCE_CHOICES,
        default='telegram',
        verbose_name="Источник"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='unauthorized',
    )
    max_daily_messages = models.IntegerField(default=50)  # Максимальное количество сообщений в день
    remaining_messages = models.IntegerField(default=50)
    last_reset_date = models.DateField(default=datetime.date.today)
    phone = models.CharField(max_length=55,)
    user_id = models.CharField(max_length=55, null=True, blank=True)
    app_hash = models.CharField(max_length=55, null=True, blank=True)
    qr = models.TextField(null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)

    def __str__(self):
        return f"{self.title} ({self.phone})"


class Chat(models.Model):
    class Meta:
        verbose_name = "Чаты"
        verbose_name_plural = "Чаты"

    previous_status = None

    def message_count(self):
        return ChatMessages.objects.filter(
            chat_id=self,
            message_type="incoming"
        ).count()

    def last_message(self):
        last_message = ChatMessages.objects.filter(
            chat_id=self,
            message_type="incoming"
        ).order_by('-created_at')\
             .first()
        if last_message is not None:
            return last_message.user_message
        else:
            return ''

    @staticmethod
    def post_save(sender, instance, created, **kwargs):
        if instance.previous_status != instance.status and instance.status != 'active':
            pipeline = CrmPipelines.objects.filter(
                project_id=instance.project_id,
                trigger=instance.status
            )

            if pipeline:
                integration_name = pipeline.project.integrations
                if integration_name == 'amo_crm':
                    r = requests.get(url="https://integration.eliment.ai/amo/lead", params={
                        'pipeline_id': pipeline.remote_pipeline_id,
                        'remote_step_id': pipeline.remote_step_id,
                        'remote_lead_id': instance.remote_lead_id,
                        'user_name': instance.tg_id,
                        'phone':  instance.phone,
                    })
                    if r.status_code == 200 and instance.remote_lead_id is None:
                        lead_action_response=json.loads(r.content)
                        instance.remote_lead_id = lead_action_response.lead_id
                        instance.save()


                if integration_name == 'bitrix':
                    r = requests.get(url="https://integration.eliment.ai/bitrix/lead", params={
                        'pipeline_id': pipeline.remote_pipeline_id,
                        'remote_step_id': pipeline.remote_step_id,
                        'remote_lead_id': instance.remote_lead_id,
                        'user_name': instance.tg_id,
                        'phone':  instance.phone,
                    })
                    if r.status_code == 200 and instance.remote_lead_id is None:
                        lead_action_response=json.loads(r.content)
                        instance.remote_lead_id = lead_action_response.lead_id
                        instance.save()



    @staticmethod
    def remember_state(sender, instance, **kwargs):
        instance.previous_state = instance



    CHAT_STATUS = [
        ('new', 'Новый'),
        ('success', 'Успешные диалоги'),
        ('contact_received', 'Контакт получен'),
        ('interest_shown', 'Проявлен интерес'),
        ('closed', 'Закрыт'),
    ]

    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    user_id = models.CharField(max_length=1000)
    user_name = models.CharField(max_length=1000, default='')
    channel = models.ForeignKey(Channel, on_delete=models.CASCADE, default=0)
    status = models.CharField(max_length=55, default="new")
    sex = models.IntegerField(null=True)
    remote_lead_id = models.IntegerField(null=True)
    phone = models.CharField(max_length=55, null=True)
    is_auto_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    last_message_time = models.DateTimeField(auto_now_add=False, null=True)


post_save.connect(Chat.post_save, sender=Chat)
post_init.connect(Chat.remember_state, sender=Chat)


class ChatMessages(models.Model):
    class Meta:
        verbose_name = "Чаты"
        verbose_name_plural = "Чаты"

    MESSAGE_TYPE = [
        ('outcoming', 'Исходящее'),
        ('incoming', 'Входящее'),
    ]

    @staticmethod
    def post_save(sender, instance, created, **kwargs):
        chat = Chat.objects.filter(
            id=instance.chat_id.id
        ).first()
        chat.last_message_time=instance.created_at
        chat.save()

    chat_id = models.ForeignKey(Chat, on_delete=models.CASCADE)
    messageId = models.CharField(null=True, max_length=1000)
    message_type = models.CharField(
        max_length=20,
        choices=MESSAGE_TYPE,
        default=None,
    )
    status = models.CharField(max_length=55, default="active") #TODO del
    user_name = models.CharField(max_length=55, )
    user_message = models.CharField(max_length=555, )
    created_at = models.DateTimeField(auto_now_add=True, null=True)


post_save.connect(ChatMessages.post_save, sender=ChatMessages)


class CrmPipelines(models.Model):
    class Meta:
        verbose_name = "Воронки проектов в CRМ"
        verbose_name_plural = "Воронки"

    TRIGGER_ACTIONS = [
        ('success', 'Успешные диалоги'),
        ('contact_received', 'Контакт получен'),
        ('interest_shown', 'Проявлен интерес'),
        ('closed', 'Закрытые'),
    ]

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE
    )
    remote_name = models.CharField(max_length=1000)
    remote_step_id = models.CharField(max_length=1000, default='')
    remote_pipeline_id = models.IntegerField(null=True)
    trigger = models.CharField(
        max_length=40,
        choices=TRIGGER_ACTIONS,
        verbose_name="Статус общения"
    )

    updated_at = models.DateTimeField(auto_now=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)

    def __str__(self):
        return f"{self.trigger} ({self.remote_name})"
