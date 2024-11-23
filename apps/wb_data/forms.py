from django import forms


class AddAPIToken(forms.Form):
    api_name = forms.CharField(max_length=200)
    api_key = forms.CharField(max_length=1000)


class AddSupplierTokens(forms.Form):
    api_token_64 = forms.CharField(max_length=1000)
    api_token_new = forms.CharField(max_length=1000)
    supplier_id = forms.IntegerField()
    

