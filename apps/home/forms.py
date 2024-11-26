# -*- encoding: utf-8 -*-
import numbers
import re
from calendar import month
from urllib import request

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
    class Meta:
        model = Project
        fields = [
            'title',
            'work_option',
            'gpt_version',
            'prompt',
            # 'file',
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Введите название проекта'}),
            'work_option': forms.Select(attrs={'class': 'form-control'}),
            'gpt_version': forms.Select(attrs={'class': 'form-control'}),
            'prompt': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Введите промпт'}),
            'file': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'client': 'Клиент',
            'title': 'Название проекта',
            'status': 'Статус',
            'work_option': 'Опции работы',
            'gpt_version': 'Версия GPT',
            'prompt': 'Список ID',
            'file': 'Файл',
        }



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
    
    tg_ids = forms.CharField(widget=forms.Textarea, label="Telegram IDs")

    def clean_tg_ids(self):
        ids = self.cleaned_data['tg_ids']
        return [int(id.strip()) for id in ids.split(',') if id.strip().isdigit()]

    class Meta:
        
        model = Recipient
        fields = [
            'title',
            'work_option',
            'tg_id',
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Введите название списка'}),
            'work_option': forms.Select(attrs={'class': 'form-control'}),
            'tg_id': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Введите тг ид список'}),
        }
        labels = {
            'client': 'Клиент',
            'title': 'Название проекта',
            'status': 'Статус',
            'work_option': 'Опции работы',
            'tg_id': 'tg id',
            'prompt': 'Промпт',
        }
    



