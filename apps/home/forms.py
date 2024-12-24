# -*- encoding: utf-8 -*-
import numbers
import re
from calendar import month
from urllib import request
import json
import datetime
import requests
from django import forms
from django.contrib.auth import get_user_model
from django.core.validators import RegexValidator
from django.forms import fields
from django import forms
from .models import Project, Recipient, TgID, Channel, ProjectFile, CrmPipelines
from django.core.exceptions import ValidationError
from django.forms import modelformset_factory
from django.db.models import Q
import json
from django.core.serializers.json import DjangoJSONEncoder
import os 



class Account(forms.Form):
    first_name = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    last_name = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    phone = forms.CharField(
        widget=forms.TextInput(attrs={"class": "form-control", "data-tel-input": ""})
    )
    email = forms.EmailField(
        required=False, widget=forms.EmailInput(attrs={"class": "form-control"})
    )
    password1 = forms.CharField(
        required=False,
        widget=forms.PasswordInput(
            attrs={"placeholder": "введите пароль", "class": "form-control"}
        ),
    )
    password2 = forms.CharField(
        required=False,
        widget=forms.PasswordInput(
            attrs={"placeholder": "повторите пароль", "class": "form-control"}
        ),
    )

    class Meta:
        # model = get_user_model()
        fields = ("first_name", "last_name", "phone", "email", "password")

    def clean_password2(self):
        cd = self.cleaned_data
        if cd["password1"] != cd["password2"]:
            raise forms.ValidationError("Passwords don't match.")
        return cd["password2"]

    def clean_phone(self):
        phone = self.cleaned_data["phone"]
        phone = (
            phone.replace("(", "").replace(")", "").replace("-", "").replace(" ", "")
        )
        if phone.startswith("8"):
            phone = "+7" + phone[1:]
        if len(phone) < 11:
            raise forms.ValidationError("Неверный формат теелфона")
        return phone



class ClientSettingsForm(forms.Form):
    sms_cloud = forms.CharField(
        label="sms_cloud",
        max_length=600,
        validators=[
            RegexValidator(
                regex="sms\.blacro\.ru\/\?u=.+&p=.+",
                message="Wrong link",
            ),
        ],
    )

    def clean_sms_cloud(self):
        data = self.cleaned_data["sms_cloud"]
        r = requests.get(data)
        if "table-striped" not in r.text:
            raise forms.ValidationError("Ссылка нерабочая")
        return data

class ProjectFileForm(forms.ModelForm):
    class Meta:
        model = ProjectFile
        fields = ['file']
        widgets = {
            'file': forms.FileInput(attrs={
                # 'multiple': True,  # Позволяет выбирать несколько файлов
                'class': 'form-control',
            }),
        }

ProjectFileFormSet = modelformset_factory(
    ProjectFile,
    form=ProjectFileForm,
    extra=6,  # Позволяет загружать до 6 файлов
)

class ProjectForm(forms.ModelForm):

    channel = forms.ModelMultipleChoiceField(
        queryset=Channel.objects.all(),
        required=True,  # Делаем выбор каналов обязательным
        widget=forms.SelectMultiple(attrs={'class': 'form-control'}),
        label="Каналы"
    )
    recipients = forms.ModelMultipleChoiceField(
        queryset=Recipient.objects.all(),
        required=False,  # Делаем выбор получателей обязательным
        widget=forms.SelectMultiple(attrs={'class': 'form-control'}),
        label="Получатели"
    )

    pipelines = forms.CharField(
            widget=forms.HiddenInput(),
            required=False
    )

    time_start = forms.TimeField(
        required=True,
        widget=forms.TimeInput(attrs={
            'type': 'time',
            'class': 'form-control',
        }),
        label="Начало времени"
    )
    time_end = forms.TimeField(
        required=True,
        widget=forms.TimeInput(attrs={
            'type': 'time',
            'class': 'form-control',
        }),
        label="Конец времени"
    )
    hello_text = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Введите приветственное сообщение',
        }),
        label="Приветственное сообщение"
    )
    knowledge_base_text = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 6,
            'placeholder': 'Введите текст базы знаний...'
        }),
        label="Текстовый файл базы знаний"
    )

    google_doc = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Введите URL Google-документа',
            'class': 'form-control',
        }),
        error_messages={
            'invalid': 'Введите правильный URL.',
        }
    )

    per_conversation_limit = forms.IntegerField(
        label="Лимит на одну переписку",
        required=False,
        initial=50,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Введите лимит'
        })
    )
    outgoing_limit = forms.IntegerField(
        required=True,
        initial=30,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Введите ограничение на исходящие сообщения',
        }),
        label="Дневной лимит",
        help_text="Суточный лимит на отправку исходящих сообщений с одного канала. На входящие сообщения не распространяется."
    )
    agent_type = forms.ChoiceField(
        choices=[
            ('sales_manager', 'Менеджер по продажам'),
            ('consultant', 'Консультант'),
            ('support_manager', 'Менеджер поддержки'),
            ('review_manager', 'Менеджер по работе с отзывами'),
            ('info_business_manager', 'Менеджер для инфобиза'),
            ('services_manager', 'Менеджер в сфере услуг'),
            ('health_fitness_manager', 'Менеджер в сфере здоровья и фитнеса'),
        ],
        required=True,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label="Тип ИИ-агента"
    )
   
    class Meta:
        model = Project
        CRM_TYPES = [
            ('null', 'не выбрано'),
            ('amo_crm', 'Amo Crm'),
            ('bitrix', 'Bitrix 24')
        ]

        fields = [
            'title',
            'work_option',
            'gpt_version',
            'prompt',
            'integrations',
            'time_start',
            'time_end',
            'hello_text',
            'knowledge_base_text',
            'google_doc',
            'outgoing_limit',
            'per_conversation_limit',
            'agent_type',
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Введите название проекта'}),
            'work_option': forms.Select(attrs={'class': 'form-control'}),
            'gpt_version': forms.Select(attrs={'class': 'form-control'}),
            'prompt': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Введите промпт'}),
            'integrations': forms.RadioSelect(attrs={'name': 'rating'}, choices=CRM_TYPES)
        }
        labels = {
            'title': 'Название проекта',
            'work_option': 'Опции работы',
            'gpt_version': 'Версия GPT',
            'prompt': 'Описание',
            'time_start': 'Начало времени',
            'time_end': 'Конец времени',
            'hello_text': 'Приветственное сообщение',
            'knowledge_base_text': 'Текстовый файл базы знаний',
            'file': 'Файл',
            'google_doc': 'Google-документ',
            'outgoing_limit': 'Дневной лимит',
            'per_conversation_limit': 'Лимит на одну переписку',
        }

    def clean_pipelines(self):
        pipelines_data = self.cleaned_data.get("pipelines", "[]")
        if not pipelines_data:
            return []
        try:
            return json.loads(pipelines_data)
        except json.JSONDecodeError:
            return []

    def get_default_work_option(self):
        # Пример настройки опций в зависимости от типа агента
        if self.agent_type == 'sales_manager':
            return 'Опция для менеджера по продажам'
        elif self.agent_type == 'consultant':
            return 'Опция для консультанта'
        if self.agent_type == 'support_manager':
            return 'Менеджер поддержки'
        elif self.agent_type == 'review_manager':
            return 'Менеджер по работе с отзывами'
        # ('info_business_manager', 'Менеджер для инфобиза'),
        # ('services_manager', 'Менеджер в сфере услуг'),
        return ''

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        project = kwargs.get('instance', None)
        self.agent_type = kwargs.pop('agent_type', None)
        super().__init__(*args, **kwargs)

        self.fields['integrations'].required = False

        print(self.agent_type)
        if self.agent_type:
            self.fields['agent_type'].initial = self.agent_type

        if user:
            self.fields['channel'].queryset = Channel.objects.filter(client=user, project_id__isnull=True, status='authorized')
            self.fields['recipients'].queryset = Recipient.objects.filter(client=user,project_id__isnull=True, status='active')

        # Устанавливаем значения по умолчанию для time_start и time_end
        if not self.instance.pk:  # Если объект модели ещё не сохранён
            self.fields['time_start'].initial = datetime.time(8, 0)
            self.fields['time_end'].initial = datetime.time(22, 0)

        else:
            user = project.client_id
            # Загружаем связанные записи для редактирования
            self.fields['channel'].queryset = Channel.objects.filter(
                Q(project_id__isnull=True) | Q(project_id=self.instance.id),
                client=user,
                status='authorized')
            self.fields['channel'].initial = Channel.objects.filter(
                project_id=self.instance.id,
                client=user,
                status='authorized'
            )
            self.fields['recipients'].queryset = Recipient.objects.filter(
                Q(project_id__isnull=True) | Q(project_id=self.instance.id),
                client=user,
                status='active')
            self.fields['recipients'].initial = Recipient.objects.filter(
                project_id=self.instance.id,
                client=user,
                status='active')

            values_list = CrmPipelines.objects.filter(
                project_id=self.instance.id) \
                .values('remote_name', 'remote_step_id', 'trigger', 'remote_pipeline_id')
            self.fields['pipelines'].initial = json.dumps(list(values_list), cls=DjangoJSONEncoder)

    def save(self, commit=True):
        project = super().save(commit=commit)
        
        # Обработка каналов
        new_channels = set(self.cleaned_data.get('channel', []))
        if self.instance.pk:  # Если это редактирование существующего проекта
            # Получаем текущие каналы проекта
            current_channels = set(Channel.objects.filter(project_id=self.instance.pk))
            
            # Находим каналы, которые нужно освободить (убрать project_id)
            channels_to_free = current_channels - new_channels
            Channel.objects.filter(id__in=[c.id for c in channels_to_free]).update(project_id=None)
            
            # Находим новые каналы, которые нужно привязать
            channels_to_assign = new_channels - current_channels
            Channel.objects.filter(id__in=[c.id for c in channels_to_assign]).update(project_id=project.id)
        else:
            # Для нового проекта просто привязываем все выбранные каналы
            Channel.objects.filter(id__in=[c.id for c in new_channels]).update(project_id=project.id)

        # Аналогичная обработка для получателей
        new_recipients = set(self.cleaned_data.get('recipients', []))
        if self.instance.pk:
            current_recipients = set(Recipient.objects.filter(project_id=self.instance.pk))
            
            # Освобождаем старых получателей
            recipients_to_free = current_recipients - new_recipients
            Recipient.objects.filter(id__in=[r.id for r in recipients_to_free]).update(project_id=None)
            
            # Привязываем новых получателей
            recipients_to_assign = new_recipients - current_recipients
            Recipient.objects.filter(id__in=[r.id for r in recipients_to_assign]).update(project_id=project.id)
        else:
            # Для нового проекта привязываем всех выбранных получателей
            Recipient.objects.filter(id__in=[r.id for r in new_recipients]).update(project_id=project.id)

        # Обработка пайплайнов
        pipelines = self.cleaned_data.get('pipelines', [])
        if commit:
            CrmPipelines.objects.filter(project_id=project).delete()
            crm_pipelines = [
                CrmPipelines(
                    project_id=project.id,
                    remote_name=pipeline['remote_name'],
                    remote_step_id=pipeline['remote_step_id'],
                    remote_pipeline_id=pipeline['remote_pipeline_id'],
                    trigger=pipeline['trigger']
                ) for pipeline in pipelines
            ]
            CrmPipelines.objects.bulk_create(crm_pipelines)

        return project


class ChannelForm(forms.ModelForm):
    def __init__(self, *args, client=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.client = client

    phone = forms.CharField(
    widget=forms.Textarea(attrs={
        'class': 'form-control',
        'placeholder': (
            'Введите номера телефонов, каждый с новой строки, например:\n'
            '+1234567890\n'
            '+1 (234) 567-8900\n'
            '+44 20 7946 0958\n'
            '+91-9876543210\n'
            '+61 412 345 678\n'
            '+49-151-12345678'
        ),
        'rows': 5,
    }),
    label="Телефоны",
    required=True
    )


    def clean_phone(self):
        phone_data = self.cleaned_data.get('phone', '')
        if not phone_data.strip():
            raise forms.ValidationError("Введите хотя бы один номер телефона.")

        # Разделяем телефонные номера по строкам
        phones = [line.strip() for line in phone_data.split('\n') if line.strip()]

        # Убираем пробелы, скобки и любые символы, кроме цифр и "+"
        cleaned_phones = []
        for phone in phones:
            cleaned_phone = re.sub(r'[^\d+]', '', phone)  # Убираем все символы, кроме "+ и цифр"
            # if not cleaned_phone.startswith('+'):
            #     raise forms.ValidationError(f"Номер телефона {phone} должен начинаться с '+'.")
            # if Channel.objects.filter(phone=cleaned_phone).exists():
            #     raise forms.ValidationError(f"Номер телефона {cleaned_phone} уже существует в базе данных.")
            cleaned_phones.append(cleaned_phone)

        return cleaned_phones

   

    def save(self, commit=True):
        """
        Сохраняет только каналы с телефонами, пропуская создание пустого канала.
        """
        # Не сохраняем базовую модель
        channel = super().save(commit=False)
        
        if not channel.client_id:
            channel.client = self.initial.get('client')

        # Получаем список телефонов из очищенных данных
        phone_list = [phone for phone in self.cleaned_data.get('phone', []) if phone.strip()]
        
        if not phone_list:
            return None

        created_channels = []
        
        # Создаем каналы только для непустых телефонов
        for index, phone in enumerate(phone_list):
            if Channel.objects.filter(phone=phone).exists():
                continue
                
            title = f"{channel.title} {index + 1}" if len(phone_list) > 1 else channel.title
            
            new_channel = Channel.objects.create(
                client=channel.client,
                title=title,
                source=channel.source,
                phone=phone,
                status=channel.status,
                is_active=True
            )
            created_channels.append(new_channel)

        # Возвращаем первый созданный канал или None
        return created_channels[0] if created_channels else None

    class Meta:
        model = Channel
        fields = ['title', 'source']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Введите название канала'}),
            'source': forms.Select(attrs={'class': 'form-control'}),
        }
        labels = {
            'title': 'Название канала',
            'source': 'Источник',
        }


class RecipientForm(forms.ModelForm):
    tg_ids = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Введите список Telegram ID или имен пользователей, разделяя их запятыми или с новой строки'
        }),
        label="Telegram IDs or Usernames",
        required=False
    )

    def clean_tg_ids(self):
        ids = self.cleaned_data.get('tg_ids', '')
        if not ids:
            return []

        # Разделяем идентификаторы по запятой или новой строке
        tg_ids = [id.strip() for id in ids.replace('\n', ',').split(',') if id.strip()]

        if not tg_ids:
            raise forms.ValidationError("Введите хотя бы один Telegram ID или имя пользователя.")

        return tg_ids

    def save(self, commit=True):
        recipient = super().save(commit=commit)
        tg_ids = self.cleaned_data.get('tg_ids', [])
        if commit:
            # Удаляем старые записи, связанные с этим Recipient
            TgID.objects.filter(recipient=recipient).delete()
            # Создаем новые записи
            TgID.objects.bulk_create(
                [TgID(recipient=recipient, tg_id=tg_id) for tg_id in tg_ids]
            )
        return recipient

    class Meta:
        model = Recipient
        fields = [
            'title',
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Введите название списка'}),
        }
        labels = {
            'title': 'Название списка',
        }
