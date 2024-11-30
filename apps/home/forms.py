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
from .models import Project, Recipient, TgID, Channel
from django.core.exceptions import ValidationError

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



class ProjectForm(forms.ModelForm):
    channel = forms.ModelMultipleChoiceField(
        queryset=Channel.objects.all(),
        required=True,  # Делаем выбор каналов обязательным
        widget=forms.SelectMultiple(attrs={'class': 'form-control'}),
        label="Каналы"
    )
    recipients = forms.ModelMultipleChoiceField(
        queryset=Recipient.objects.all(),
        required=True,  # Делаем выбор получателей обязательным
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

    class Meta:
        model = Project
        fields = [
            'title',
            'work_option',
            'gpt_version',
            'prompt',
            'time_start',
            'time_end',
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
        }


    def __init__(self, *args, **kwargs):
            user = kwargs.pop('user', None)
            super().__init__(*args, **kwargs)

            if user:
                # Ограничиваем выбор каналов для текущего пользователя
                self.fields['channel'].queryset = Channel.objects.filter(client=user, project_id__isnull=True, status='active')
                # Ограничиваем выбор получателей для текущего пользователя
                self.fields['recipients'].queryset = Recipient.objects.filter(client=user, project_id__isnull=True, status='active')

            # Устанавливаем значения по умолчанию для time_start и time_end
            if not self.instance.pk:  # Если объект модели ещё не сохранён
                self.fields['time_start'].initial = datetime.time(8, 0)
                self.fields['time_end'].initial = datetime.time(22, 0)
                
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
    class Meta:
        model = Channel
        fields = [
            'title',
            'phone',
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Введите название проекта'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Введите телефон'}),
        }
        labels = {
            'title': 'Название проекта',
            'phone': 'Телефон',
        }

    def clean_phone(self):
        phone = self.cleaned_data.get('phone')
        if not phone:
            raise ValidationError("Поле телефона обязательно для заполнения.")
        
        # Проверка формата: должен начинаться с "+" и содержать только цифры после
        if not re.match(r'^\+\d+$', phone):
            raise ValidationError("Введите номер телефона в международном формате, начиная с '+', например, +1234567890.")
        
        return phone


class RecipientForm(forms.ModelForm):
    tg_ids = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control', 
            'rows': 4, 
            'placeholder': 'Введите список Telegram ID, разделяя их запятыми'
        }),
        label="Telegram IDs",
        required=False
    )

    def clean_tg_ids(self):
        ids = self.cleaned_data.get('tg_ids', '')
        if not ids:
            return []
        tg_ids = [id.strip() for id in ids.split(',') if id.strip().isdigit()]
        if not tg_ids:
            raise forms.ValidationError("Введите хотя бы один корректный Telegram ID.")
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
            'work_option',
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Введите название списка'}),
            'work_option': forms.Select(attrs={'class': 'form-control'}),
        }
        labels = {
            'title': 'Название списка',
            'work_option': 'Опции работы',
        }



