from django.db import models
from django.contrib.auth.models import AbstractUser, Group, Permission
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import BaseUserManager
import uuid
from django.utils import timezone
from datetime import timedelta
import os

def company_image_upload_path(instance: 'Company', filename: str) -> str:
    ext = filename.split('.')[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    return os.path.join('company_images', filename)

def user_profile_image_upload_path(instance: 'UserInfo', filename: str) -> str:
    ext = filename.split('.')[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    return os.path.join('profile_images', filename)

class Company(models.Model):
    name = models.CharField(max_length=100)
    company_domain = models.CharField(max_length=100, unique=False,null=True,blank=True)
    image = models.ImageField(upload_to=company_image_upload_path, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.name

class UserManager(BaseUserManager):
    def _create_user(self, email, password=None, **extra_fields):
        """
        Creates and saves a User with the given email and password.
        """
        if not email:
            raise ValueError('Users must have an email address')
        
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self._create_user(email, password, **extra_fields)

class Domain(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    name = models.CharField(max_length=50, unique=False)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.name

class User(AbstractUser):
    ROLE_CHOICES = [
        ('Company_owner', 'Company Owner'),
        ('Project_manager', 'Project Manager'),
        ('Team_lead', 'Team Lead'),
        ('Sub_team_lead', 'Sub Team Lead'),
        ('Employee','Employee'),
    ]

    username = None
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='employees')
    domain = models.ForeignKey(Domain, on_delete=models.SET_NULL, null=True, blank=True)
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=25, choices=ROLE_CHOICES)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['company','role','domain','is_active']

    objects = UserManager()
    
    def __str__(self) -> str:
        return self.email

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'

class UserInfo(models.Model):
    class StatusChoices(models.TextChoices):
        ONLINE = 'online', 'Online'
        OFFLINE = 'offline', 'Offline'
    
    THEME_CHOICES = [
        ('light', 'Light'),
        ('dark', 'Dark'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='info')
    first_name = models.CharField(max_length=50,null=True,blank=True)
    last_name = models.CharField(max_length=50,null=True,blank=True)
    phone = models.CharField(max_length=15, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    theme = models.CharField(max_length=10, choices=THEME_CHOICES, default='dark')
    status = models.CharField(max_length=10, choices=StatusChoices.choices, default=StatusChoices.OFFLINE)
    profile_image = models.ImageField(upload_to=user_profile_image_upload_path, null=True, blank=True)
    skills = models.TextField(blank=True, null=True)
    otp = models.CharField(max_length=6,null=True,blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def set_online(self):
        self.status = self.StatusChoices.ONLINE
        self.save()
    
    def set_offline(self):
        self.status = self.StatusChoices.OFFLINE
        self.save()
    
    def get_todays_duration(self) :
        from attendance.models import LoginLogout
        from django.db.models import Sum
        today = timezone.now().date()
        records = LoginLogout.objects.filter(
            user=self,
            date=today,
            duration__isnull=False
        )
        total = records.aggregate(total=Sum('duration'))['total']
        return total or timedelta(0)