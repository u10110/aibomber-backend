import numbers
import re
from calendar import month
from urllib import request

import requests
from django import forms
from django.contrib.auth import get_user_model
from django.core.validators import RegexValidator
from django.forms import fields


class PhraseIntersection(forms.Form):
    groupA = forms.CharField(widget=forms.Textarea)
    groupB = forms.CharField(widget=forms.Textarea)
