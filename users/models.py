import logging
from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.db import models

logger = logging.getLogger(__name__)

phone_validator = RegexValidator(
    regex=r'^\+380\d{9}$',
    message="Phone should start with +380 and contain 9 more digits."
)

class CustomUser(AbstractUser):


    email = models.EmailField(unique=True)
    phone = models.CharField( max_length=13,unique=True,validators=[phone_validator])
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)

    is_email_verified = models.BooleanField(default=False)
    email_verification_code = models.CharField(max_length=6, blank=True, null=True)

    REQUIRED_FIELDS = ['email', 'phone', 'first_name', 'last_name']

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if is_new:
            logger.info(f"New user created: {self.REQUIRED_FIELDS} (ID: {self.pk})")
        else:
            logger.info(f"User updated: {self.REQUIRED_FIELDS} (ID: {self.pk})")

    def __str__(self):
        return self.first_name


