from django.db import models


class EmailServiceProviderChoices(models.TextChoices):
    """
    Email Service Provider Options Used in Campaign Model
    """
    GMAIL = 'gmail', "GMAIL"
    OUTLOOK = 'outlook', "OUTLOOK"


class PaymentStatusChoices(models.TextChoices):
    """
    Payment Options Used in Payment Model
    """
    INCOMPLETE = "incomplete", "INCOMPLETE"
    PENDING = "pending", "PENDING"
    SUCCESS = "success", "SUCCESS"


class DomainTypes(models.TextChoices):
    """
    Domain Types Used in Selecting Domain in Campaign Configuration
    """
    NEW = "new_domain", "NEW DOMAIN"
    MAINTAIN = "maintain_deliverability", "MAINTAIN DELIVERABILITY"
    REPAIR = "repair", "REPAIR DOMAIN"
    CUSTOM = "custom", "CUSTOM DOMAIN"


class MaxEmailPerDay(models.TextChoices):
    """
    Max Email Per Day used in Campaign Based on Domain Type
    """
    NEW = 30, "30"
    MAINTAIN = 50, "50"
    REPAIR = 100, "100"
    CUSTOM = 75, "75"


class EmailStepUp(models.TextChoices):
    """
    StepUp Count used in Campaign Based on Domain Type
    """
    NEW = 3, "3"
    MAINTAIN = 5, "5"
    REPAIR = 10, "10"
    CUSTOM = 7, "7"


class CampaignActionRequiredChoices(models.TextChoices):
    """
    Choices for Action Required for Campaign Model
    """
    PAYMENT_AND_APP_PASSWORD_BOTH_REQUIRED = "payment_and_app_password", "PAYMENT AND APP PASSWORD BOTH REQUIRED"
    APP_PASSWORD_REQUIRED = "app_password", "APP PASSWORD REQUIRED"
    PAYMENT_REQUIRED = "payment", "PAYMENT REQUIRED"
    NONE = None, "NO ACTION REQUIRED"
