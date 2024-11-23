# -*- encoding: utf-8 -*-
from pyexpat import model
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


class UserManager(BaseUserManager):
    """Define a model manager for User model with no username field."""

    def _create_user(self, phone, password=None, **extra_fields):
        """Create and save a User with the given phone and password."""
        if not phone:
            raise ValueError("The given phone must be set")
        user = self.model(phone=phone, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, phone, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(phone, password, **extra_fields)

    def create_superuser(self, phone, password=None, **extra_fields):
        """Create and save a SuperUser with the given phone and password."""
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self._create_user(phone, password, **extra_fields)


class User(AbstractUser):
    phone = models.CharField(max_length=15, null=True, unique=True)
    username = models.CharField(unique=False, max_length=50)
    code = models.CharField(max_length=50, null=True)
    last_sms_date = models.DateTimeField(null=True)
    objects = UserManager()

    USERNAME_FIELD = "phone"
    REQUIRED_FIELDS = []

    def __str__(self):
        return str(self.id)


class UserInfo(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    sex = models.IntegerField(null=True)
    date_birthday = models.DateField(null=True)
