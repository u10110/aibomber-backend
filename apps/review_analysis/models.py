from django.db import models
from apps.authentication.models import User


class ReviewsAnalysis(models.Model):
    client = models.ForeignKey(User, on_delete=models.CASCADE)
    status = models.CharField(max_length=55)
    sku_list = models.JSONField()
    numb_reviews = models.IntegerField(null=True)
    average_rate = models.FloatField(null=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
# Create your models here.
