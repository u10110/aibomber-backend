from django import forms


class ActualBidsForm(forms.Form):
    type_advertise = forms.CharField(max_length=100)
    to_search = forms.CharField(max_length=300)


