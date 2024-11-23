# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

from operator import le
from django import forms
# from django.contrib.auth.forms import UserCreationForm
from .models import User
import re




class LoginForm(forms.Form):
    phone = forms.CharField(widget=forms.TextInput(
            attrs={
                "placeholder": "введите номер телефона",
                "class": "form-control",
                'data-tel-input': ''
            }
        ))
    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                "placeholder": "введите пароль",
                "class": "form-control"
            }
        ))
    


class SignUpForm(forms.ModelForm):
    phone = forms.CharField(widget=forms.TextInput(
            attrs={
                "placeholder": "введите номер телефона",
                "class": "form-control",
                'data-tel-input': ''
            }
        ))
    password1 = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                "placeholder": "введите пароль",
                "class": "form-control"
            }
        ))
    password2 = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                "placeholder": "повторите пароль",
                "class": "form-control"
            }
        ))
        
    class Meta:
        model = User
        fields = ('phone', 'password1', 'password2')
    

    def clean_password2(self):
        cd = self.cleaned_data
        if cd['password1'] != cd['password2']:
            raise forms.ValidationError('Passwords don\'t match.')
        return cd['password2']
    
    def clean_phone(self):
        phone = self.cleaned_data['phone']
        phone = phone.replace('(', '').replace(')', '').replace('-', '').replace(' ', '')
        if phone.startswith('8'):
            phone = '+7' + phone[1:]
        if len(phone) < 11:
            raise forms.ValidationError('Неверный формат теелфона')
        return phone
