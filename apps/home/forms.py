# -*- encoding: utf-8 -*-
import numbers
import re
from calendar import month
from urllib import request

import datetime
import requests
from django import forms
from django.contrib.auth import get_user_model
from django.core.validators import RegexValidator
from django.forms import fields
from django import forms
from .models import Project, Recipient, TgID, Channel, ProjectFile
from django.core.exceptions import ValidationError
from django.forms import modelformset_factory


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
            'file': forms.ClearableFileInput(attrs={
                'class': 'form-control',
                'multiple': True,  # Разрешить выбор нескольких файлов
                'accept': '.pdf,.txt,.doc,.docx,.xlsx,.csv,.xslm'
            }),
        }
        labels = {
            'file': 'Файл',
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

    file = forms.FileField(
        required=False,
        widget=forms.ClearableFileInput(attrs={
            'class': 'form-control',
            'accept': '.pdf,.txt,.doc,.docx,.xlsx,.csv,.xslm'
        }),
        label="Файл"
    )
    google_doc = forms.URLField(
        required=False,
        widget=forms.URLInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ссылка на Google-документ',
        }),
        label="Google-документ"
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
        fields = [
            'title',
            'work_option',
            'gpt_version',
            'prompt',
            'time_start',
            'time_end',
            'hello_text',
            'knowledge_base_text',
            'file',
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
        self.agent_type = kwargs.pop('agent_type', None)
        super().__init__(*args, **kwargs)

        print(self.agent_type)
        if self.agent_type:
            self.fields['agent_type'].initial = self.agent_type

        if user:
            self.fields['channel'].queryset = Channel.objects.filter(client=user, project_id__isnull=True, status='authorized')
            self.fields['recipients'].queryset = Recipient.objects.filter(client=user, project_id__isnull=True, status='active')

        # Устанавливаем значения по умолчанию для time_start и time_end
        if not self.instance.pk:  # Если объект модели ещё не сохранён
            self.fields['time_start'].initial = datetime.time(8, 0)
            self.fields['time_end'].initial = datetime.time(22, 0)
        else:
            # Загружаем связанные записи для редактирования
            self.fields['channel'].initial = Channel.objects.filter(client=user, project_id=self.instance.id, status='authorized')
            self.fields['recipients'].initial = Recipient.objects.filter(client=user, project_id=self.instance.id, status='active')


    def save(self, commit=True):
        # Сохраняем объект проекта
        project = super().save(commit=commit)

        # Обновляем поле project_id в связанных каналах
        channels = self.cleaned_data.get('channel', [])
        for channel in channels:
            channel.project_id = project.id
            channel.save()

        # Обновляем поле project_id в связанных получателях
        recipients = self.cleaned_data.get('recipients', [])
        for recipient in recipients:
            recipient.project_id = project.id
            recipient.save()

        return project


class ChannelForm(forms.ModelForm):
    def __init__(self, *args, client=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.client = client

    phone = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'placeholder': 'Введите номера телефонов, каждый с новой строки, например: +1234567890',
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
        Сохраняет канал и создает записи для каждого номера телефона.
        """
        channel = super().save(commit=False)

        if not channel.client_id:
            channel.client = self.initial.get('client')
        if commit:
            channel.save()  # Сохраняем канал в базе данных

        # Получаем список телефонов из очищенных данных
        phone_list = self.cleaned_data.get('phone', [])  # Это уже список из clean_phone

        # Удаляем старые записи, связанные с этим каналом
        Channel.objects.filter(title=channel.title, source=channel.source).delete()

        # Создаем новую запись для каждого номера
        for phone in phone_list:
            if not Channel.objects.filter(client=self.client, phone=phone).exists():
                Channel.objects.create(
                    client=channel.client,
                    title=channel.title,
                    source=channel.source,
                    phone=phone,
                    status=channel.status,
                    is_active="True"
                )


        return channel

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
