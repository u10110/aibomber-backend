from django.db import models
from apps.authentication.models import User
from apps.home.models import ClientSettings


class API_tokens(models.Model):
    token = models.CharField(max_length=1000)
    updated_at = models.DateTimeField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)

class Orders(models.Model):
    date = models.DateTimeField()
    sku = models.IntegerField()
    name = models.TextField()
    brand = models.CharField(max_length=200)
    price = models.IntegerField()
    income_id = models.IntegerField()
    token = models.ForeignKey(API_tokens, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)


class Sales(models.Model):
    name = models.TextField()
    date = models.DateTimeField()
    sku = models.IntegerField()
    brand = models.CharField(max_length=200)
    price = models.IntegerField()
    income_id = models.IntegerField()
    token = models.ForeignKey(API_tokens, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)


class Client_tokens(models.Model):
    token = models.ForeignKey(API_tokens, on_delete=models.CASCADE)
    name = models.TextField()
    client = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)


class Client_Supplier_Access(models.Model):
    client_settings = models.ForeignKey(ClientSettings, on_delete=models.CASCADE)
    api_token_64 = models.TextField(null=True)
    api_token_new = models.TextField(null=True)
    supplier_id = models.IntegerField(null=True)





