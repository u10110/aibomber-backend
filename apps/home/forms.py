# -*- encoding: utf-8 -*-
import numbers
import re
from calendar import month
from urllib import request

import requests
from apps.home.models import (
    AddingReview,
    BoostLike,
    ClientCard,
    ClientProduct,
    ClientPvz,
    Marketplace,
    ProductBuyout,
)
from django import forms
from django.contrib.auth import get_user_model
from django.core.validators import RegexValidator
from django.forms import fields


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


class AddSku(forms.Form):
    marketplace = forms.CharField(label="marketplace", max_length=100)
    key_phrase = forms.CharField(label="key_phrase", max_length=300)
    size = forms.CharField(label="size", max_length=300, required=False)
    sku = forms.IntegerField(label="sku")
    sex = forms.IntegerField(label="sku")
    count_item = forms.IntegerField(label="count_item")
    buyout_date_start = forms.DateField(label="buyout_date_start")
    buyout_date_end = forms.DateField(label="buyout_date_end")
    is_dbs = forms.CharField(max_length=300, required=True)
    pvz_selected = forms.CharField(max_length=5000, required=True)
    group_num = forms.IntegerField()
    pay_type = forms.CharField(required=True, max_length=10)
    tg_start_date = forms.TimeField(required=False)
    tg_end_date = forms.TimeField(required=False)


class AddingReviewForm(forms.ModelForm):
    text = forms.CharField(widget=forms.Textarea, min_length=10, max_length=1000)
    star = forms.IntegerField()
    review_date = forms.DateTimeField()
    file = forms.FileField(
        widget=forms.ClearableFileInput(attrs={"multiple": True}), required=False
    )
    # photo = forms.ImageField(upload_to='img/reviews/')
    # status = forms.TextField(default="available")
    class Meta:
        model = AddingReview
        fields = ["review_date", "star", "text",]


class AddPvz(forms.Form):
    marketplace = forms.CharField(label="marketplace", max_length=100, required=False)
    address = forms.CharField(label="address", widget=forms.Textarea)


class AddDBS(forms.Form):
    marketplace = forms.CharField(label="marketplace", max_length=100)
    country = forms.CharField(label="country", max_length=100)
    city = forms.CharField(label="city", max_length=100)
    region = forms.CharField(label="region", max_length=100, required=False)
    locality = forms.CharField(label="locality", max_length=100)
    street = forms.CharField(label="street", max_length=100, required=False)
    building = forms.IntegerField(label="building")
    building_k = forms.IntegerField(label="building_k", required=False)
    building_s = forms.IntegerField(label="building_s", required=False)
    apartament = forms.IntegerField(label="apartament", required=False)
    entrance = forms.IntegerField(label="entrance", required=False)
    intercom = forms.IntegerField(label="intercom", required=False)
    floor = forms.IntegerField(label="floor", required=False)


class AddCardForm(forms.Form):
    model = ClientCard
    number = forms.CharField(label="number", max_length=55)
    month = forms.CharField(label="month", max_length=2)
    year = forms.CharField(label="year", max_length=2)
    cvc = forms.CharField(label="cvc", max_length=3)

    def clean_number(self):
        data = self.cleaned_data["number"].replace(" ", "")
        print(data)
        if (
            re.match(
                r"^(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|6(?:011|5[0-9][0-9])[0-9]{12}|3[47][0-9]{13}|3(?:0[0-5]|[68][0-9])[0-9]{11}|(?:2131|1800|35\d{3})\d{11})|(2[0-9]{15})$",
                data,
            )
            is None
        ):
            print("bad")
            raise forms.ValidationError("Карта некорректна")
        return data


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


class BoostLikeForm(forms.Form):
    marketplace = forms.CharField(label="marketplace", max_length=100)
    # product = forms.CharField(label='product', max_length=300)
    url = forms.CharField(
        label="url",
        validators=[
            RegexValidator(
                regex="wildberries\.ru/(catalog|brands)/",
                message="Wrong link",
            ),
        ],
    )
    count = forms.IntegerField(label="count")
    # count_done = forms.IntegerField(label='count_done')


class ClientProductForm(forms.ModelForm):
    # this form work with model ClentProduct
    model = ClientProduct
    # on the page will be view files:
    fields = ["marketplace", "sku"]
    fields = "__all__"


class QuestionForm(forms.Form):
    sku = forms.IntegerField(label="sku")
    question_text = forms.CharField(max_length=1000)
    question_date = forms.DateField()
    sex = forms.IntegerField()


class Wb_token(forms.Form):
    token = forms.CharField(max_length=1000)


class SearchPromotionForm(forms.Form):
    marketplace = forms.CharField(label="marketplace", max_length=100, required=False)
    # product = forms.CharField(label='product', max_length=300)
    sku = forms.IntegerField(label="sku")
